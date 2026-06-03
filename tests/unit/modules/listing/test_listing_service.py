from __future__ import annotations

from typing import Any, cast

import pytest

from app.core.errors import RateLimitError
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
from app.modules.business.listing.services.listing import ListingService
from app.modules.business.listing.services.quota import ListingQuotaService
from app.modules.business.listing.stores.listing import ListingStore
from app.modules.business.listing.types import (
    AddressVersionType,
    AuthorType,
    StyleType,
)
from tests.factories import build_test_settings


class _Quota:
    def __init__(self, reserve_error: Exception | None = None) -> None:
        self.calls: list[str] = []
        self.reserve_error = reserve_error
        self.usage = RemainResponse(
            used_requests=1,
            total_requests=100,
            reset_date="2026-06-04 00:00:00",
        )

    async def reserve(self, user_id: str) -> str:
        self.calls.append(f"reserve:{user_id}")
        if self.reserve_error is not None:
            raise self.reserve_error
        return "reservation-1"

    async def finalize(self, reservation: Any) -> RemainResponse:
        self.calls.append(f"finalize:{reservation}")
        return self.usage

    async def refund(self, reservation: Any) -> RemainResponse:
        self.calls.append(f"refund:{reservation}")
        return self.usage

    async def get_remaining_request(self, user_id: str) -> RemainResponse:
        self.calls.append(f"remaining:{user_id}")
        return self.usage

    async def reset_request(self, user_id: str) -> RemainResponse:
        self.calls.append(f"reset:{user_id}")
        return self.usage

    async def reset_all_requests(self) -> None:
        self.calls.append("reset_all")


class _Generation:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.error = error

    async def generate(self, **kwargs: Any) -> ListingGenerationResult:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return ListingGenerationResult(title="Title", description="Description")


class _Store:
    def __init__(self) -> None:
        self.created: list[Any] = []
        self.found: list[Any] | None = None

    async def create_listing(self, listing: Any) -> Any:
        self.created.append(listing)
        return listing

    async def get_listing(self, listing_id: str, user_id: str) -> list[Any] | None:
        return self.found


def _params() -> AllParams:
    return AllParams(
        goal="bán",
        property_type="nhà",
        area=50.0,
        price=2_000_000_000.0,
        price_unit="VND",
        city="HCM",
        district="1",
        ward="1",
        contact_name="Anh A",
        contact_phone="0900",
    )


def _pair_params() -> PairAddressParams:
    return PairAddressParams(
        **_params().model_dump(),
        new_city="TP.HCM",
        new_ward="Phường Bến Nghé",
    )


def _service(
    *,
    quota: _Quota | None = None,
    description: _Generation | None = None,
    pair_address: _Generation | None = None,
    store: _Store | None = None,
) -> tuple[ListingService, _Quota, _Generation, _Generation, _Store]:
    resolved_quota = quota or _Quota()
    resolved_description = description or _Generation()
    resolved_pair_address = pair_address or _Generation()
    resolved_store = store or _Store()
    service = ListingService(
        store=cast(ListingStore, resolved_store),
        quota=cast(ListingQuotaService, resolved_quota),
        description_generation=cast(DescriptionGenerationService, resolved_description),
        pair_address_generation=cast(
            PairAddressGenerationService, resolved_pair_address
        ),
        settings=build_test_settings(),
    )
    return (
        service,
        resolved_quota,
        resolved_description,
        resolved_pair_address,
        resolved_store,
    )


async def test_generate_description_reserves_and_finalizes_quota():
    service, quota, description, _, _ = _service()

    result = await service.generate_description(
        user_id="u1",
        listing_id="l1",
        style=StyleType.SIMPLE,
        params=_params(),
        address_version=AddressVersionType.OLD,
    )

    assert result.title == "Title"
    assert result.description == "Description"
    assert result.usage.used_requests == 1
    assert quota.calls == ["reserve:u1", "finalize:reservation-1"]
    assert description.calls[0]["listing_id"] == "l1"


async def test_generate_pair_address_uses_pair_generator():
    service, quota, description, pair_address, _ = _service()

    await service.generate_pair_address(
        user_id="u1",
        listing_id="l1",
        style=StyleType.SIMPLE,
        params=_pair_params(),
        address_version=AddressVersionType.NEW,
    )

    assert quota.calls == ["reserve:u1", "finalize:reservation-1"]
    assert description.calls == []
    assert pair_address.calls[0]["address_version"] == AddressVersionType.NEW


async def test_generate_failure_refunds_quota_and_reraises():
    error = RuntimeError("generation failed")
    service, quota, _, _, _ = _service(description=_Generation(error=error))

    with pytest.raises(RuntimeError, match="generation failed"):
        await service.generate_description(
            user_id="u1",
            listing_id="l1",
            style=StyleType.SIMPLE,
            params=_params(),
            address_version=AddressVersionType.OLD,
        )

    assert quota.calls == ["reserve:u1", "refund:reservation-1"]


async def test_quota_exceeded_propagates_without_refund():
    rate_limit = RateLimitError(message="Quota exceeded")
    service, quota, description, _, _ = _service(quota=_Quota(reserve_error=rate_limit))

    with pytest.raises(RateLimitError):
        await service.generate_description(
            user_id="u1",
            listing_id="l1",
            style=StyleType.SIMPLE,
            params=_params(),
            address_version=AddressVersionType.OLD,
        )

    assert quota.calls == ["reserve:u1"]
    assert description.calls == []


async def test_submit_and_get_listing_use_store_with_legacy_metadata():
    store = _Store()
    service, _, _, _, _ = _service(store=store)
    payload = SubmitListing(
        user_id="u1",
        listing_id="l1",
        title="Nhà đẹp",
        description="Mô tả",
        style=StyleType.SIMPLE,
    )

    await service.submit_listing(payload)
    store.found = store.created
    found = await service.get_listing(listing_id="l1", user_id="u1")

    assert found == store.created
    assert store.created[0].author == AuthorType.USER
    assert store.created[0].version == build_test_settings().VERSION


async def test_usage_methods_delegate_to_listing_quota_service():
    service, quota, _, _, _ = _service()

    remaining = await service.get_remaining_request("u1")
    reset = await service.reset_request("u1")
    await service.reset_all_requests()
    service.change_day_limit(7)

    assert remaining.used_requests == 1
    assert reset.used_requests == 1
    assert quota.calls == ["remaining:u1", "reset:u1", "reset_all"]
