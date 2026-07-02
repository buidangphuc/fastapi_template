"""Legacy `POST /description` (ported from
bds-genai-dgl core/generator/api/v1/description.py), behavior- and
envelope-compatible.

Flow: call the listing use-case service and return the legacy envelope. The
service owns reserve/finalize/refund; exhausted quota still raises 429 before
generation runs.
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.api.legacy.listing_dependencies import get_listing_service
from app.api.legacy.response import LegacyResponseModel, legacy_response
from app.core.errors import RateLimitError
from app.modules.business.listing.schemas import AllParams, DescriptionResponse
from app.modules.business.listing.services.listing import ListingService
from app.modules.business.listing.types import (
    AddressVersionType,
    StyleType,
)

router = APIRouter()


@router.post("/description", summary="Generate Description")
async def generate_description(
    params: AllParams,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    try:
        generated = await service.generate_description(
            user_id=user_id,
            listing_id=listing_id,
            style=style,
            params=params,
            address_version=address_version,
        )

        return await legacy_response.success(
            data=DescriptionResponse(
                title=generated.title,
                description=generated.description,
                usage=generated.usage,
            )
        )
    except RateLimitError:
        raise
    except Exception:
        logger.error(f"Error generating description: {traceback.format_exc()}")
        return await legacy_response.fail()
