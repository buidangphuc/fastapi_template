from __future__ import annotations

from app.core.config import Settings
from app.modules.business.listing.schemas import RemainResponse
from app.modules.business.listing.types import DATETIME_FORMAT
from app.modules.platform.quota.models import (
    QuotaPolicy,
    QuotaReservation,
    QuotaUsage,
)
from app.modules.platform.quota.service import QuotaService

LISTING_GENERATION_QUOTA_RESOURCE = "legacy.listing.generate"
SECONDS_PER_DAY = 86_400


class ListingQuotaService:
    def __init__(
        self,
        quota: QuotaService,
        settings: Settings,
    ) -> None:
        self._quota = quota
        self._settings = settings

    async def reserve(self, user_id: str) -> QuotaReservation:
        return await self._quota.reserve(
            subject_id=user_id,
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            policy=self._policy(),
        )

    async def finalize(self, reservation: QuotaReservation) -> RemainResponse:
        usage = await self._quota.finalize(reservation)
        return self._legacy_usage_response(usage)

    async def refund(self, reservation: QuotaReservation) -> RemainResponse:
        usage = await self._quota.refund(reservation)
        return self._legacy_usage_response(usage)

    async def get_remaining_request(self, user_id: str) -> RemainResponse:
        usage = await self._quota.get_usage(
            subject_id=user_id,
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            policy=self._policy(),
        )
        return self._legacy_usage_response(usage)

    async def reset_request(self, user_id: str) -> RemainResponse:
        usage = await self._quota.reset_usage(
            subject_id=user_id,
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            policy=self._policy(),
        )
        return self._legacy_usage_response(usage)

    async def reset_all_requests(self) -> None:
        await self._quota.reset_resource(LISTING_GENERATION_QUOTA_RESOURCE)

    def _policy(self) -> QuotaPolicy:
        return QuotaPolicy(
            resource=LISTING_GENERATION_QUOTA_RESOURCE,
            limit=self._settings.MAX_USAGE_LIMIT_PER_USER,
            window_seconds=self._settings.MAX_RESET_LIMIT_DAYS * SECONDS_PER_DAY,
        )

    @staticmethod
    def _legacy_usage_response(usage: QuotaUsage) -> RemainResponse:
        return RemainResponse(
            used_requests=usage.used,
            total_requests=usage.limit,
            reset_date=usage.reset_at.strftime(DATETIME_FORMAT),
        )


def build_listing_quota_service(
    quota: QuotaService,
    settings: Settings,
) -> ListingQuotaService:
    return ListingQuotaService(quota, settings)
