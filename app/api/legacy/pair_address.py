"""Legacy `POST /description/pair_address` (ported from
bds-genai-dgl core/generator/api/v1/pair_address.py).

Mounted under the `/description` prefix in ``app/api/legacy/router.py`` so the
full path matches legacy byte-for-byte (`/api/v1/description/pair_address`).

Same flow as `/description` but with the pair-address use-case and
`PairAddressParams`/`PairAddressDescriptionResponse`.
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.api.legacy.listing_dependencies import get_listing_service
from app.api.legacy.response import LegacyResponseModel, legacy_response
from app.core.errors import RateLimitError
from app.modules.business.listing.schemas import (
    PairAddressDescriptionResponse,
    PairAddressParams,
)
from app.modules.business.listing.services.listing import ListingService
from app.modules.business.listing.types import (
    AddressVersionType,
    StyleType,
)

router = APIRouter()


@router.post("/pair_address", summary="Generate Pair Address Description")
async def generate_pair_address_description(
    params: PairAddressParams,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    style: StyleType = Query(description="Style"),
    address_version: AddressVersionType = Query(default=AddressVersionType.OLD),
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    try:
        generated = await service.generate_pair_address(
            user_id=user_id,
            listing_id=listing_id,
            style=style,
            params=params,
            address_version=address_version,
        )

        return await legacy_response.success(
            data=PairAddressDescriptionResponse(
                title=generated.title,
                description=generated.description,
                usage=generated.usage,
            )
        )
    except RateLimitError:
        raise
    except Exception:
        logger.error(
            f"Error generating pair-address description: {traceback.format_exc()}"
        )
        return await legacy_response.fail()
