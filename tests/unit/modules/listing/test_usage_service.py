from datetime import datetime, timedelta

from app.modules.business.listing.services.usage import UsageService
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


def _service(**overrides):
    settings = build_test_settings(**overrides)
    gateway = FakeMongoGateway()
    return UsageService(gateway, settings), gateway, settings


async def test_get_remaining_creates_user_when_missing():
    service, _, _ = _service()
    data = await service.get_remaining_request("u1")
    assert data["used_requests"] == 0
    assert data["total_requests"] == 100
    assert data["reset_date"]
    assert await service.get_user("u1") is not None


async def test_increase_request_accumulates():
    service, _, _ = _service()
    await service.get_remaining_request("u1")
    user = await service.get_user("u1")
    assert user is not None
    await service.increase_request(user, 3)
    data = await service.get_remaining_request("u1")
    assert data["used_requests"] == 3


async def test_reset_after_limit_days():
    service, gateway, settings = _service()
    await service.get_remaining_request("u1")
    user = await service.get_user("u1")
    assert user is not None
    await service.increase_request(user, 5)
    collection = gateway.collection(settings.MONGODB_USAGE_COLLECTION)
    collection.docs[0]["first_request_date"] = datetime.now() - timedelta(
        days=settings.MAX_RESET_LIMIT_DAYS + 1
    )
    data = await service.get_remaining_request("u1")
    assert data["used_requests"] == 0


async def test_delete_all_users():
    service, _, _ = _service()
    await service.get_remaining_request("u1")
    await service.delete_all_users()
    assert await service.get_user("u1") is None


async def test_total_requests_reflects_settings_override():
    service, _, _ = _service(MAX_USAGE_LIMIT_PER_USER=42)
    data = await service.get_remaining_request("u1")
    assert data["total_requests"] == 42
