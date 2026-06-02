from datetime import datetime
from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.api.legacy.deps import get_description_generator
from app.bootstrap.application import create_app
from app.modules.business.listing.handlers.description import (
    Content,
    Description,
    DescriptionGenerator,
    Title,
)
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


def _app():
    settings = build_test_settings(
        MONGO_ENABLED=True,
        GMAP_PG_ENABLE=False,
        PROJECT_ENABLE=False,
        CHAT_MODEL="openai:gpt-4o-mini",
    )
    app = create_app(settings=settings, init_resources=False)
    app.state.resources.mongo = FakeMongoGateway()
    content = Content(
        title=Title(output="Bán nhà Q1"),
        description=Description(output="Liên hệ <contact_name> <contact_phone>"),
        quality_score=0.9,
    )
    generator = DescriptionGenerator(
        nearby_service=None,
        project_service=None,
        chat_model=_StubChat(content, {"input_tokens": 11, "output_tokens": 22}),
        settings=settings,
    )
    app.dependency_overrides[get_description_generator] = lambda: generator
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


async def test_generate_description_quota_exceeded_returns_429():
    app = _app()
    await app.state.resources.mongo.collection(
        app.state.settings.MONGODB_USAGE_COLLECTION
    ).insert_one(
        {
            "user_id": "u2",
            "used_requests": 100,
            "first_request_date": datetime.now(),
        }
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description",
            params={"user_id": "u2", "listing_id": "l1", "style": "simple"},
            json=_params_body(),
        )
    assert response.status_code == 429
