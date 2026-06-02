from httpx import ASGITransport, AsyncClient

from app.bootstrap.application import create_app
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


def _app(mongo_enabled: bool = True):
    app = create_app(
        settings=build_test_settings(MONGO_ENABLED=mongo_enabled),
        init_resources=False,
    )
    if mongo_enabled:
        app.state.resources.mongo = FakeMongoGateway()
    return app


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_usage_limit_creates_user_and_returns_envelope():
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


async def test_legacy_routes_absent_when_mongo_disabled():
    app = _app(mongo_enabled=False)
    async with _client(app) as client:
        response = await client.get("/api/v1/usage_limit/u1")
    assert response.status_code == 404
