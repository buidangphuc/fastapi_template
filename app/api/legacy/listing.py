"""Legacy listing submit/get endpoints (ported from
bds-genai-dgl core/submit/api/v1/listing.py), behavior- and envelope-compatible.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.api.legacy.listing_dependencies import get_listing_service
from app.api.legacy.response import (
    LegacyResponseModel,
    legacy_response,
)
from app.modules.business.listing.schemas import SubmitListing
from app.modules.business.listing.services.listing import ListingService

router = APIRouter()


@router.post("/listing/submit", description="Submit a listing")
async def submit_listing(
    submit_listing: SubmitListing,
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    logger.info(f"Submitting listing for user_id: {submit_listing.user_id}")
    await service.submit_listing(submit_listing)
    return await legacy_response.success(message="Listing created successfully")


@router.get("/listing", description="Get a listing")
async def get_listing(
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    listing = await service.get_listing(listing_id=listing_id, user_id=user_id)
    if not listing:
        return await legacy_response.success(message="Listing not found")
    return await legacy_response.success(
        data=[item.model_dump(mode="json") for item in listing]
    )
