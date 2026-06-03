from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.bootstrap.application import create_app
from app.bootstrap.services import LISTING_SERVICE_NAME, build_listing_runtime
from app.modules.business.listing.generation.description import (
    Content,
    Description,
    Title,
)
from app.modules.platform.quota.factory import build_quota_service
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


class _StubStructured:
    def __init__(self, content: Content, usage: dict) -> None:
        self._content = content
        self._usage = usage

    async def ainvoke(self, messages, config=None):
        return {
            "parsed": self._content,
            "raw": SimpleNamespace(usage_metadata=self._usage),
            "parsing_error": None,
        }


class _StubChat:
    def __init__(self, content: Content, usage: dict) -> None:
        self._content = content
        self._usage = usage

    def with_structured_output(self, schema, include_raw: bool = False):
        return _StubStructured(self._content, self._usage)


class _StubHttpClient:
    async def request(self, *args, **kwargs):
        raise AssertionError("HTTP client should not be used in this test")

    async def aclose(self):
        return None


def _app(**overrides):
    settings = build_test_settings(
        MONGO_ENABLED=True,
        QUOTA_ENABLED=True,
        QUOTA_BACKEND="mongo",
        GMAP_PG_ENABLE=False,
        PROJECT_ENABLE=False,
        CHAT_MODEL="openai:gpt-4o-mini",
        **overrides,
    )
    app = create_app(settings=settings, init_resources=False)
    app.state.resources.mongo = FakeMongoGateway()
    app.state.resources.quota = build_quota_service(
        app.state.settings,
        mongo=app.state.resources.mongo,
    )
    content = Content(
        title=Title(output="Bán nhà Q1"),
        description=Description(output="Liên hệ <contact_name> <contact_phone>"),
        quality_score=0.9,
    )
    app.state.resources.services[LISTING_SERVICE_NAME] = build_listing_runtime(
        settings=app.state.settings,
        mongo=app.state.resources.mongo,
        quota=app.state.resources.quota,
        http_client=_StubHttpClient(),
        chat_model=_StubChat(content, {"input_tokens": 11, "output_tokens": 22}),
    )
    return app


def _params_body():
    return {
        "goal": "bán",
        "property_type": "nhà",
        "area": 50.0,
        "price": 2_000_000_000.0,
        "price_unit": "VND",
        "city": "HCM",
        "district": "1",
        "ward": "1",
        "contact_name": "Anh A",
        "contact_phone": "0900",
    }


async def test_generate_description_happy_path():
    app = _app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description",
            params={"user_id": "u1", "listing_id": "l1", "style": "simple"},
            json=_params_body(),
        )
        usage = await client.get("/api/v1/usage_limit/u1")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "OK"
    assert body["data"]["title"] == "Bán nhà Q1"
    assert "Anh A" in body["data"]["description"]
    assert "0900" in body["data"]["description"]
    assert "<contact_phone>" not in body["data"]["description"]
    assert body["data"]["usage"]["used_requests"] == 1
    assert body["data"]["usage"]["total_requests"] == 100
    assert usage.json()["data"]["used_requests"] == 1


async def test_generate_description_quota_exceeded_returns_429():
    app = _app(MAX_USAGE_LIMIT_PER_USER=1)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post(
            "/api/v1/description",
            params={"user_id": "u2", "listing_id": "l1", "style": "simple"},
            json=_params_body(),
        )
        response = await client.post(
            "/api/v1/description",
            params={"user_id": "u2", "listing_id": "l2", "style": "simple"},
            json=_params_body(),
        )
    assert first.status_code == 200
    assert response.status_code == 429
