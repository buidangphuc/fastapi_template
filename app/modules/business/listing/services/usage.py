"""Per-user usage quota service (30-day reset window).

Ported behavior-frozen from bds-genai-dgl ``core/limiter/service/usage.py``.
The only structural change: the Mongo handle is injected (lifespan-managed
``MongoGateway``) instead of an import-time singleton, and limits are read live
from ``Settings`` so the legacy ``PUT /day_limit`` runtime override is honored.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.core.config import Settings
from app.modules.business.listing.config import DATETIME_FORMAT
from app.modules.business.listing.models import UsageUser
from app.modules.platform.mongo.gateway import MongoGateway


class UsageService:
    def __init__(self, gateway: MongoGateway, settings: Settings) -> None:
        self._users = gateway.collection(settings.MONGODB_USAGE_COLLECTION)
        self._settings = settings

    async def get_user(self, user_id: str) -> UsageUser | None:
        user_data = await self._users.find_one({"user_id": user_id})
        if user_data:
            return UsageUser(**user_data)
        return None

    async def create_user(self, user_id: str) -> UsageUser:
        user = UsageUser(
            user_id=user_id,
            used_requests=0,
            first_request_date=datetime.now(),
        )
        await self._users.insert_one(user.model_dump(by_alias=True))
        return user

    async def delete_all_users(self) -> None:
        await self._users.delete_many({})

    async def increase_request(self, user: UsageUser, request_count: int = 1) -> None:
        user.used_requests += request_count
        await self._users.update_one(
            {"user_id": user.user_id},
            {"$set": {"used_requests": user.used_requests}},
        )

    async def reset_request(self, user: UsageUser) -> None:
        current_date = datetime.now()
        user.used_requests = 0
        user.first_request_date = current_date
        await self._users.update_one(
            {"user_id": user.user_id},
            {
                "$set": {
                    "used_requests": user.used_requests,
                    "first_request_date": user.first_request_date,
                }
            },
        )

    async def get_remaining_request(self, user_id: str) -> dict[str, Any]:
        user = await self.get_user(user_id)
        if user is None:
            user = await self.create_user(user_id)
        current_date = datetime.now()
        days_since_first_request = (current_date - user.first_request_date).days

        if days_since_first_request >= self._settings.MAX_RESET_LIMIT_DAYS:
            await self.reset_request(user)
        reset_date = user.first_request_date + timedelta(
            days=self._settings.MAX_RESET_LIMIT_DAYS
        )
        reset_date_str = reset_date.strftime(DATETIME_FORMAT)
        return {
            "used_requests": user.used_requests,
            "total_requests": self._settings.MAX_USAGE_LIMIT_PER_USER,
            "reset_date": reset_date_str,
        }
