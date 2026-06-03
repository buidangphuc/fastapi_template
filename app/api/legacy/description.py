"""Legacy `POST /description` (ported from
bds-genai-dgl core/generator/api/v1/description.py), behavior- and
envelope-compatible.

Flow: reserve usage quota → pick template from the user's recent AI listings →
generate → background-submit the listing → finalize quota → return the legacy
envelope. Body errors refund the reservation and return ``response_base.fail()``
(matching legacy); exhausted quota raises 429 before generation runs.
"""

from __future__ import annotations

import traceback
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from loguru import logger

from app.api.legacy.deps import (
    get_description_generator,
    get_listing_quota_service,
    get_listing_store,
)
from app.api.legacy.response import ResponseModel, response_base
from app.bootstrap.state import get_app_settings
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
from app.modules.business.listing.services.quota import ListingQuotaService
from app.modules.business.listing.templates import select_template

router = APIRouter()


async def _submit_listing(store: ListingStore, listing: Listing) -> None:
    await store.create_listing(listing)
    logger.info(f"Listing submitted for user_id: {listing.user_id}")


@router.post("/description", summary="Generate Description")
async def generate_description(
    request: Request,
    background_tasks: BackgroundTasks,
    params: AllParams,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    generator: DescriptionGenerator = Depends(get_description_generator),
    quota: ListingQuotaService = Depends(get_listing_quota_service),
    store: ListingStore = Depends(get_listing_store),
) -> ResponseModel:
    quota_reservation = await quota.reserve(user_id)
    quota_finalized = False
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
        usage_response = await quota.finalize(quota_reservation)
        quota_finalized = True

        return await response_base.success(
            data=DescriptionResponse(
                title=data["title"],
                description=data["description"],
                usage=usage_response,
            )
        )
    except Exception:
        if not quota_finalized:
            try:
                await quota.refund(quota_reservation)
            except Exception:
                logger.error(f"Error refunding quota: {traceback.format_exc()}")
        logger.error(f"Error generating description: {traceback.format_exc()}")
        return await response_base.fail()
