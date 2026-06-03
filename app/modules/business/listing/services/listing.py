"""Use-case boundary for the legacy listing product."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loguru import logger

from app.core.config import Settings
from app.modules.business.listing.models import Listing
from app.modules.business.listing.schemas import (
    AllParams,
    PairAddressParams,
    RemainResponse,
    SubmitListing,
)
from app.modules.business.listing.services.generation import (
    DescriptionGenerationService,
    ListingGenerationResult,
    PairAddressGenerationService,
)
from app.modules.business.listing.services.quota import ListingQuotaService
from app.modules.business.listing.stores.listing import ListingStore
from app.modules.business.listing.types import (
    AddressVersionType,
    AuthorType,
    StyleType,
)


@dataclass(frozen=True)
class ListingGeneratedResponse:
    title: str
    description: str
    usage: RemainResponse


class ListingService:
    def __init__(
        self,
        *,
        store: ListingStore,
        quota: ListingQuotaService,
        description_generation: DescriptionGenerationService,
        pair_address_generation: PairAddressGenerationService,
        settings: Settings,
    ) -> None:
        self._store = store
        self._quota = quota
        self._description_generation = description_generation
        self._pair_address_generation = pair_address_generation
        self._settings = settings

    async def generate_description(
        self,
        *,
        user_id: str,
        listing_id: str,
        style: StyleType,
        params: AllParams,
        address_version: AddressVersionType,
    ) -> ListingGeneratedResponse:
        return await self._generate_with_quota(
            user_id=user_id,
            generate=lambda: self._description_generation.generate(
                user_id=user_id,
                listing_id=listing_id,
                style=style,
                params=params,
                address_version=address_version,
            ),
        )

    async def generate_pair_address(
        self,
        *,
        user_id: str,
        listing_id: str,
        style: StyleType,
        params: PairAddressParams,
        address_version: AddressVersionType,
    ) -> ListingGeneratedResponse:
        return await self._generate_with_quota(
            user_id=user_id,
            generate=lambda: self._pair_address_generation.generate(
                user_id=user_id,
                listing_id=listing_id,
                style=style,
                params=params,
                address_version=address_version,
            ),
        )

    async def submit_listing(self, submit_listing: SubmitListing) -> None:
        listing = Listing(
            user_id=submit_listing.user_id,
            listing_id=submit_listing.listing_id,
            title=submit_listing.title,
            description=submit_listing.description,
            style=submit_listing.style,
            author=AuthorType.USER,
            created_date=datetime.now(),
            platform=submit_listing.platform,
            version=self._settings.VERSION,
        )
        await self._store.create_listing(listing=listing)

    async def get_listing(
        self,
        *,
        listing_id: str,
        user_id: str,
    ) -> list[Listing] | None:
        return await self._store.get_listing(listing_id=listing_id, user_id=user_id)

    async def get_remaining_request(self, user_id: str) -> RemainResponse:
        return await self._quota.get_remaining_request(user_id=user_id)

    async def reset_request(self, user_id: str) -> RemainResponse:
        return await self._quota.reset_request(user_id=user_id)

    async def reset_all_requests(self) -> None:
        await self._quota.reset_all_requests()

    def change_day_limit(self, limit: int) -> None:
        self._settings.MAX_RESET_LIMIT_DAYS = limit

    async def _generate_with_quota(
        self,
        *,
        user_id: str,
        generate: Any,
    ) -> ListingGeneratedResponse:
        reservation = await self._quota.reserve(user_id)
        try:
            generated: ListingGenerationResult = await generate()
            usage_response = await self._quota.finalize(reservation)
            return ListingGeneratedResponse(
                title=generated.title,
                description=generated.description,
                usage=usage_response,
            )
        except Exception:
            try:
                await self._quota.refund(reservation)
            except Exception:
                logger.error(f"Error refunding quota: {traceback.format_exc()}")
            raise
