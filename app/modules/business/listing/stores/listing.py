"""Submitted-listing persistence.

Ported behavior-frozen from bds-genai-dgl ``core/submit/service/listing.py``;
only the Mongo handle is injected (lifespan-managed) instead of an import-time
singleton.
"""

from __future__ import annotations

from app.core.config import Settings
from app.modules.business.listing.models import Listing
from app.modules.business.listing.types import StyleType
from app.modules.platform.mongo.gateway import MongoGateway


class ListingStore:
    def __init__(self, gateway: MongoGateway, settings: Settings) -> None:
        self._submit = gateway.collection(settings.MONGODB_SUBMIT_COLLECTION)

    async def get_listing(self, listing_id: str, user_id: str) -> list[Listing] | None:
        listings = [
            Listing(**doc)
            async for doc in self._submit.find(
                {"listing_id": listing_id, "user_id": user_id}
            )
        ]
        return listings or None

    async def get_last_listing_by_ai(
        self,
        user_id: str,
        style: StyleType,
        num_listing: int = 2,
    ) -> list[Listing] | None:
        cursor = (
            self._submit.find(
                {"user_id": user_id, "author": "ai", "style": style.value}
            )
            .sort("created_date", -1)
            .limit(num_listing)
        )
        listings = [Listing(**doc) async for doc in cursor]
        return listings or None

    async def get_recent_ai_template_ids(
        self,
        user_id: str,
        style: StyleType,
        limit: int = 2,
    ) -> list[str | None]:
        cursor = (
            self._submit.find(
                {"user_id": user_id, "author": "ai", "style": style.value},
                {"template_id": 1, "_id": 0},
            )
            .sort("created_date", -1)
            .limit(limit)
        )
        return [doc.get("template_id") async for doc in cursor]

    async def create_listing(self, listing: Listing) -> Listing:
        await self._submit.insert_one(listing.model_dump(by_alias=True))
        return listing
