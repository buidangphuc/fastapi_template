from httpx import ASGITransport, AsyncClient

from app.bootstrap.application import create_app
from app.bootstrap.services import LISTING_SERVICE_NAME, build_listing_runtime
from app.modules.business.listing.services.quota import build_listing_quota_service
from app.modules.platform.quota.factory import build_quota_service
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


class _StubHttpClient:
    async def request(self, *args, **kwargs):
        raise AssertionError("HTTP client should not be used in this test")

    async def aclose(self):
        return None


def _app(mongo_enabled: bool = True):
    settings = build_test_settings(
        MONGO_ENABLED=mongo_enabled,
        QUOTA_ENABLED=mongo_enabled,
        QUOTA_BACKEND="mongo" if mongo_enabled else "memory",
    )
    app = create_app(
        settings=settings,
        init_resources=False,
    )
    if mongo_enabled:
        mongo = FakeMongoGateway()
        quota = build_quota_service(app.state.settings, mongo=mongo)
        app.state.resources.mongo = mongo
        app.state.resources.quota = quota
        app.state.resources.services[LISTING_SERVICE_NAME] = build_listing_runtime(
            settings=app.state.settings,
            mongo=mongo,
            quota=quota,
            http_client=_StubHttpClient(),
            chat_model=object(),
        )
    return app


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _consume_listing_quota(app, user_id: str) -> None:
    quota = app.state.resources.quota
    assert quota is not None
    service = build_listing_quota_service(quota, app.state.settings)
    reservation = await service.reserve(user_id)
    await service.finalize(reservation)


async def test_usage_limit_returns_legacy_envelope():
    app = _app()
    async with _client(app) as client:
        response = await client.get("/api/v1/usage_limit/u1")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "OK"
    assert body["data"]["used_requests"] == 0
    assert body["data"]["total_requests"] == 100
    assert body["data"]["reset_date"]


async def test_usage_limit_reflects_listing_quota_consumption():
    app = _app()
    await _consume_listing_quota(app, "u1")

    async with _client(app) as client:
        response = await client.get("/api/v1/usage_limit/u1")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["used_requests"] == 1
    assert body["data"]["total_requests"] == 100


async def test_reset_user_clears_listing_quota_usage():
    app = _app()
    await _consume_listing_quota(app, "u1")
    await _consume_listing_quota(app, "u2")

    async with _client(app) as client:
        reset = await client.get("/api/v1/reset/u1")
        u1 = await client.get("/api/v1/usage_limit/u1")
        u2 = await client.get("/api/v1/usage_limit/u2")

    assert reset.status_code == 200
    assert reset.json()["message"] == "Request reset successfully"
    assert u1.json()["data"]["used_requests"] == 0
    assert u2.json()["data"]["used_requests"] == 1


async def test_reset_all_clears_listing_quota_usage():
    app = _app()
    await _consume_listing_quota(app, "u1")
    await _consume_listing_quota(app, "u2")

    async with _client(app) as client:
        reset = await client.get("/api/v1/reset_all")
        u1 = await client.get("/api/v1/usage_limit/u1")
        u2 = await client.get("/api/v1/usage_limit/u2")

    assert reset.status_code == 200
    assert reset.json()["message"] == "Request reset successfully"
    assert u1.json()["data"]["used_requests"] == 0
    assert u2.json()["data"]["used_requests"] == 0


async def test_listing_submit_then_get_roundtrip():
    app = _app()
    async with _client(app) as client:
        payload = {
            "user_id": "u1",
            "listing_id": "l1",
            "title": "Nhà đẹp",
            "description": "Mô tả",
            "style": "simple",
        }
        submit = await client.post("/api/v1/listing/submit", json=payload)
        assert submit.status_code == 200
        assert submit.json()["message"] == "Listing created successfully"

        got = await client.get(
            "/api/v1/listing", params={"user_id": "u1", "listing_id": "l1"}
        )
    assert got.status_code == 200
    data = got.json()["data"]
    assert isinstance(data, list)
    assert data[0]["title"] == "Nhà đẹp"
    # Legacy datetime format "%Y-%m-%d %H:%M:%S" (space-separated, not ISO 'T').
    assert " " in data[0]["created_date"]
    assert "T" not in data[0]["created_date"]


async def test_get_listing_not_found_envelope():
    app = _app()
    async with _client(app) as client:
        response = await client.get(
            "/api/v1/listing", params={"user_id": "u1", "listing_id": "zzz"}
        )
    assert response.status_code == 200
    assert response.json()["message"] == "Listing not found"


async def test_day_limit_overrides_settings():
    app = _app()
    async with _client(app) as client:
        response = await client.put("/api/v1/day_limit", json={"limit": 7})
    assert response.status_code == 200
    assert app.state.settings.MAX_RESET_LIMIT_DAYS == 7


async def test_day_limit_updates_existing_quota_reset_date():
    app = _app()
    await _consume_listing_quota(app, "u1")

    async with _client(app) as client:
        before = await client.get("/api/v1/usage_limit/u1")
        response = await client.put("/api/v1/day_limit", json={"limit": 7})
        after = await client.get("/api/v1/usage_limit/u1")

    assert response.status_code == 200
    assert before.json()["data"]["used_requests"] == 1
    assert after.json()["data"]["used_requests"] == 1
    assert after.json()["data"]["reset_date"] != before.json()["data"]["reset_date"]


async def test_legacy_routes_absent_when_mongo_disabled():
    app = _app(mongo_enabled=False)
    async with _client(app) as client:
        response = await client.get("/api/v1/usage_limit/u1")
    assert response.status_code == 404
