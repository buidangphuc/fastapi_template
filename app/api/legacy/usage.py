"""Legacy usage-limit endpoints (ported from
bds-genai-dgl core/limiter/api/v1/usage.py), behavior- and envelope-compatible.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from loguru import logger

from app.api.legacy.deps import get_usage_service
from app.api.legacy.response import (
    CustomResponseCode,
    ResponseModel,
    response_base,
)
from app.bootstrap.state import get_app_settings
from app.modules.business.listing.schemas import ChangeDayLimit, RemainResponse
from app.modules.business.listing.services.usage import UsageService

router = APIRouter()


@router.get("/usage_limit/{user_id}", description="Get remaining requests for a user")
async def get_remaining_requests(
    request: Request,
    user_id: str = Path(description="User ID"),
    service: UsageService = Depends(get_usage_service),
) -> ResponseModel:
    logger.info(f"Getting remaining requests for user_id: {user_id}")
    data = await service.get_remaining_request(user_id=user_id)
    remain_response = RemainResponse(**data)
    return await response_base.success(data=remain_response)


@router.get("/reset/{user_id}", description="Reset remaining requests for a user")
async def reset_remaining_requests(
    request: Request,
    user_id: str = Path(description="User ID"),
    service: UsageService = Depends(get_usage_service),
) -> ResponseModel:
    logger.info(f"Reset request received for user_id: {user_id}")
    user = await service.get_user(user_id=user_id)
    if user:
        await service.reset_request(user=user)
    else:
        logger.warning(f"User not found for user_id: {user_id}")
    return await response_base.success(
        res=ResponseModel(
            code=CustomResponseCode.HTTP_200.code,
            message="Request reset successfully",
        )
    )


@router.get("/reset_all", description="Reset all remaining requests for all users")
async def reset_all(
    request: Request,
    service: UsageService = Depends(get_usage_service),
) -> ResponseModel:
    logger.info("Reset all usage limit for all users")
    await service.delete_all_users()
    return await response_base.success(
        res=ResponseModel(
            code=CustomResponseCode.HTTP_200.code,
            message="Request reset successfully",
        )
    )


@router.put("/day_limit", description="Change the day limit for all users")
async def change_day_limit(
    request: Request, day_limit: ChangeDayLimit
) -> ResponseModel:
    limit = day_limit.limit
    logger.info(f"Changing day limit to: {limit}")
    get_app_settings(request.app).MAX_RESET_LIMIT_DAYS = limit
    return await response_base.success(
        res=ResponseModel(
            code=CustomResponseCode.HTTP_200.code,
            message="Day limit changed successfully",
        )
    )
