"""Legacy `POST /description` (ported from
bds-genai-dgl core/generator/api/v1/description.py), behavior- and
envelope-compatible.

Flow: enforce usage quota (dependency) → pick template from the user's recent AI
listings → generate → background-submit the listing + increment usage → return
the legacy envelope. Errors inside the body return ``response_base.fail()``
(matching legacy); the quota dependency raises 429 before the body runs.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from loguru import logger

from app.api.legacy.deps import (
    get_description_generator,
    get_listing_store,
    get_usage_service,
)
from app.api.legacy.response import ResponseModel, response_base
from app.bootstrap.state import get_app_settings
from app.core.errors import RateLimitError
from app.modules.business.listing.config import (
    DATETIME_FORMAT,
    AddressVersionType,
    AuthorType,
    LanguageType,
    StyleType,
    ToneType,
)
from app.modules.business.listing.handlers.description import DescriptionGenerator
from app.modules.business.listing.models import Listing
from app.modules.business.listing.schemas import AllParams, DescriptionResponse
from app.modules.business.listing.services.listing_store import ListingStore
from app.modules.business.listing.services.usage import UsageService
from app.modules.business.listing.templates import select_template

router = APIRouter()


async def enforce_usage_limit(
    request: Request,
    user_id: str = Query(description="User ID"),
    service: UsageService = Depends(get_usage_service),
) -> None:
    data = await service.get_remaining_request(user_id=user_id)
    logger.info(f"User {user_id} already used {data['used_requests']} requests")
    if data["used_requests"] >= get_app_settings(request.app).MAX_USAGE_LIMIT_PER_USER:
        raise RateLimitError(
            message=f"Request limit exceeded. Retry after {data['reset_date']}",
        )


async def _submit_listing(store: ListingStore, listing: Listing) -> None:
    await store.create_listing(listing)
    logger.info(f"Listing submitted for user_id: {listing.user_id}")


async def _increase_request(service: UsageService, user_id: str) -> dict[str, Any]:
    user = await service.get_user(user_id=user_id)
    if user is not None:
        await service.increase_request(user=user, request_count=1)
    return await service.get_remaining_request(user_id=user_id)


@router.post(
    "/description",
    summary="Generate Description",
    dependencies=[Depends(enforce_usage_limit)],
)
async def generate_description(
    request: Request,
    background_tasks: BackgroundTasks,
    params: AllParams,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    generator: DescriptionGenerator = Depends(get_description_generator),
    usage: UsageService = Depends(get_usage_service),
    store: ListingStore = Depends(get_listing_store),
) -> ResponseModel:
    try:
        tone = ToneType.SIMPLE if style == StyleType.SIMPLE else ToneType.PROFESSIONAL
        last_ai_listing = await store.get_last_listing_by_ai(
            user_id=user_id, style=style, num_listing=2
        )
        template_response = select_template(
            last_ai_listing or [], style, get_app_settings(request.app)
        )
        data = await generator.agenerate(
            language=LanguageType.VI,
            tone=tone,
            style=style,
            params=params,
            template_id=template_response.selected_template,
            address_version=address_version,
        )

        listing = Listing(
            user_id=user_id,
            listing_id=listing_id,
            description=data["description"],
            title=data["title"],
            style=style,
            prompt=data["prompt"],
            author=AuthorType.AI,
            created_date=datetime.now().strftime(DATETIME_FORMAT),
            template_id=template_response.selected_template,
            prompt_tokens=data["tokens"]["usage"]["prompt_tokens"],
            completion_tokens=data["tokens"]["usage"]["completion_tokens"],
            generating_time=data["generating_time"],
            llm_model_name=data["llm_model_name"],
            user_input=params.model_dump_json(),
            platform=params.platform,
            version=get_app_settings(request.app).VERSION,
            prompt_version=data.get("prompt_version"),
        )
        background_tasks.add_task(_submit_listing, store, listing)
        usage_response = await _increase_request(usage, user_id)

        return await response_base.success(
            data=DescriptionResponse(
                title=data["title"],
                description=data["description"],
                usage=usage_response,
            )
        )
    except Exception:
        logger.error(f"Error generating description: {traceback.format_exc()}")
        return await response_base.fail()
