from datetime import datetime
from typing import Any

from app.modules.business.listing.config import DATETIME_FORMAT, AuthorType, StyleType
from app.modules.business.listing.models import Listing
from app.modules.business.listing.services.listing_store import ListingStore
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


def _store():
    settings = build_test_settings()
    gateway = FakeMongoGateway()
    return ListingStore(gateway, settings), gateway


def _listing(**overrides: Any) -> Listing:
    base: dict[str, Any] = {
        "user_id": "u1",
        "listing_id": "l1",
        "title": "t",
        "description": "d",
        "author": AuthorType.AI,
        "style": StyleType.SIMPLE,
        "created_date": datetime.now().strftime(DATETIME_FORMAT),
    }
    base.update(overrides)
    return Listing(**base)


async def test_create_and_get_listing():
    store, _ = _store()
    await store.create_listing(_listing())
    found = await store.get_listing("l1", "u1")
    assert found is not None
    assert found[0].title == "t"
    assert await store.get_listing("missing", "u1") is None


async def test_get_last_listing_by_ai_orders_newest_first_and_limits():
    store, _ = _store()
    await store.create_listing(
        _listing(listing_id="l1", created_date="2026-01-01 00:00:00")
    )
    await store.create_listing(
        _listing(listing_id="l2", created_date="2026-02-01 00:00:00")
    )
    await store.create_listing(
        _listing(listing_id="l3", created_date="2026-03-01 00:00:00")
    )
    last = await store.get_last_listing_by_ai("u1", StyleType.SIMPLE, num_listing=2)
    assert last is not None
    assert [item.listing_id for item in last] == ["l3", "l2"]


async def test_get_last_listing_by_ai_filters_non_ai_authors():
    store, _ = _store()
    await store.create_listing(_listing(author=AuthorType.USER))
    assert await store.get_last_listing_by_ai("u1", StyleType.SIMPLE) is None
