"""Legacy usage-limit endpoints (ported from
bds-genai-dgl core/limiter/api/v1/usage.py), behavior- and envelope-compatible.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path
from loguru import logger

from app.api.legacy.listing_dependencies import get_listing_service
from app.api.legacy.response import (
    LegacyResponseModel,
    legacy_response,
)
from app.modules.business.listing.schemas import ChangeDayLimit
from app.modules.business.listing.services.listing import ListingService

router = APIRouter()


@router.get("/usage_limit/{user_id}", description="Get remaining requests for a user")
async def get_remaining_requests(
    user_id: str = Path(description="User ID"),
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    logger.info(f"Getting remaining requests for user_id: {user_id}")
    remain_response = await service.get_remaining_request(user_id=user_id)
    return await legacy_response.success(data=remain_response)


@router.get("/reset/{user_id}", description="Reset remaining requests for a user")
async def reset_remaining_requests(
    user_id: str = Path(description="User ID"),
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    logger.info(f"Reset request received for user_id: {user_id}")
    await service.reset_request(user_id=user_id)
    return await legacy_response.success(message="Request reset successfully")


@router.get("/reset_all", description="Reset all remaining requests for all users")
async def reset_all(
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    logger.info("Reset all usage limit for all users")
    await service.reset_all_requests()
    return await legacy_response.success(message="Request reset successfully")


@router.put("/day_limit", description="Change the day limit for all users")
async def change_day_limit(
    day_limit: ChangeDayLimit,
    service: ListingService = Depends(get_listing_service),
) -> LegacyResponseModel:
    limit = day_limit.limit
    logger.info(f"Changing day limit to: {limit}")
    service.change_day_limit(limit)
    return await legacy_response.success(message="Day limit changed successfully")
