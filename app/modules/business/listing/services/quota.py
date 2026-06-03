from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.modules.business.listing.config import DATETIME_FORMAT
from app.modules.platform.mongo.gateway import MongoGateway
from app.modules.platform.quota.adapters.mongo import MongoQuotaStore
from app.modules.platform.quota.models import QuotaPolicy, QuotaReservation, QuotaUsage
from app.modules.platform.quota.service import QuotaService
from app.modules.platform.quota.store import StaticQuotaPolicyStore

LISTING_GENERATION_QUOTA_RESOURCE = "legacy.listing.generate"
LISTING_QUOTA_COUNTER_COLLECTION = "listing_quota_counters"
LISTING_QUOTA_RESERVATION_COLLECTION = "listing_quota_reservations"
SECONDS_PER_DAY = 86_400


@dataclass(frozen=True)
class ListingQuotaReservation:
    reservation: QuotaReservation


class ListingQuotaService:
    def __init__(self, quota: QuotaService, settings: Settings) -> None:
        self._quota = quota
        self._settings = settings

    async def reserve(self, user_id: str) -> ListingQuotaReservation:
        reservation = await self._quota.reserve(
            subject_id=user_id,
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            policy=self._policy(),
        )
        return ListingQuotaReservation(reservation=reservation)

    async def finalize(self, reservation: ListingQuotaReservation) -> dict:
        usage = await self._quota.finalize(reservation.reservation)
        return self._legacy_usage_response(usage)

    async def refund(self, reservation: ListingQuotaReservation) -> dict:
        usage = await self._quota.refund(reservation.reservation)
        return self._legacy_usage_response(usage)

    async def get_remaining_request(self, user_id: str) -> dict:
        usage = await self._quota.get_usage(
            subject_id=user_id,
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            policy=self._policy(),
        )
        return self._legacy_usage_response(usage)

    def _policy(self) -> QuotaPolicy:
        return QuotaPolicy(
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            limit=self._settings.MAX_USAGE_LIMIT_PER_USER,
            window_seconds=self._settings.MAX_RESET_LIMIT_DAYS * SECONDS_PER_DAY,
        )

    @staticmethod
    def _legacy_usage_response(usage: QuotaUsage) -> dict:
        return {
            "used_requests": usage.used,
            "total_requests": usage.limit,
            "reset_date": usage.reset_at.strftime(DATETIME_FORMAT),
        }


def build_listing_quota_service(
    gateway: MongoGateway,
    settings: Settings,
) -> ListingQuotaService:
    quota = QuotaService(
        store=MongoQuotaStore(
            gateway,
            counter_collection=LISTING_QUOTA_COUNTER_COLLECTION,
            reservation_collection=LISTING_QUOTA_RESERVATION_COLLECTION,
        ),
        policy_store=StaticQuotaPolicyStore(),
    )
    return ListingQuotaService(quota, settings)
