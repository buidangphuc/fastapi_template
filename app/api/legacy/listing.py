"""Legacy listing submit/get endpoints (ported from
bds-genai-dgl core/submit/api/v1/listing.py), behavior- and envelope-compatible.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from loguru import logger

from app.api.legacy.deps import get_listing_store
from app.api.legacy.response import (
    CustomResponseCode,
    ResponseModel,
    response_base,
)
from app.bootstrap.state import get_app_settings
from app.modules.business.listing.config import DATETIME_FORMAT, AuthorType
from app.modules.business.listing.models import Listing
from app.modules.business.listing.schemas import SubmitListing
from app.modules.business.listing.services.listing_store import ListingStore

router = APIRouter()


@router.post("/listing/submit", description="Submit a listing")
async def submit_listing(
    request: Request,
    submit_listing: SubmitListing,
    store: ListingStore = Depends(get_listing_store),
) -> ResponseModel:
    logger.info(f"Submitting listing for user_id: {submit_listing.user_id}")
    listing = Listing(
        user_id=submit_listing.user_id,
        listing_id=submit_listing.listing_id,
        title=submit_listing.title,
        description=submit_listing.description,
        style=submit_listing.style,
        author=AuthorType.USER.value,
        created_date=datetime.now().strftime(DATETIME_FORMAT),
        platform=submit_listing.platform,
        version=get_app_settings(request.app).VERSION,
    )
    await store.create_listing(listing=listing)
    return await response_base.success(
        res=ResponseModel(
            code=CustomResponseCode.HTTP_200.code,
            message="Listing created successfully",
        )
    )


@router.get("/listing", description="Get a listing")
async def get_listing(
    request: Request,
    user_id: str = Query(description="User ID"),
    listing_id: str = Query(description="Listing ID"),
    store: ListingStore = Depends(get_listing_store),
) -> ResponseModel:
    listing = await store.get_listing(listing_id=listing_id, user_id=user_id)
    if not listing:
        return await response_base.success(
            res=ResponseModel(
                code=CustomResponseCode.HTTP_200.code,
                message="Listing not found",
            )
        )
    return await response_base.success(
        data=[item.model_dump(mode="json") for item in listing]
    )
