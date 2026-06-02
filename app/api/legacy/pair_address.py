"""Legacy `POST /description/pair_address` (ported from
bds-genai-dgl core/generator/api/v1/pair_address.py).

Mounted under the `/description` prefix in ``app/api/legacy/router.py`` so the
full path matches legacy byte-for-byte (`/api/v1/description/pair_address`).

Same flow as `/description` but with the pair-address generator and
`PairAddressParams`/`PairAddressDescriptionResponse`. Reuses the quota
dependency + submit/increment helpers from the description endpoint.
"""

from __future__ import annotations

import traceback
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from loguru import logger

from app.api.legacy.deps import (
    get_listing_store,
    get_pair_address_generator,
    get_usage_service,
)
from app.api.legacy.description import (
    _increase_request,
    _submit_listing,
    enforce_usage_limit,
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
from app.modules.business.listing.handlers.pair_address import PairAddressGenerator
from app.modules.business.listing.models import Listing
from app.modules.business.listing.schemas import (
    PairAddressDescriptionResponse,
    PairAddressParams,
)
from app.modules.business.listing.services.listing_store import ListingStore
from app.modules.business.listing.services.usage import UsageService
from app.modules.business.listing.templates import select_template

router = APIRouter()


@router.post(
    "/pair_address",
    summary="Generate Pair Address Description",
    dependencies=[Depends(enforce_usage_limit)],
)
async def generate_pair_address_description(
    request: Request,
    background_tasks: BackgroundTasks,
    params: PairAddressParams,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    generator: PairAddressGenerator = Depends(get_pair_address_generator),
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
            data=PairAddressDescriptionResponse(
                title=data["title"],
                description=data["description"],
                usage=usage_response,
            )
        )
    except Exception:
        logger.error(
            f"Error generating pair-address description: {traceback.format_exc()}"
        )
        return await response_base.fail()
