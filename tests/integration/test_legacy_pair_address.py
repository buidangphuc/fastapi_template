from types import SimpleNamespace

from httpx import ASGITransport, AsyncClient

from app.api.legacy.deps import get_pair_address_generator
from app.bootstrap.application import create_app
from app.modules.business.listing.handlers.description import (
    Content,
    Description,
    Title,
)
from app.modules.business.listing.handlers.pair_address import PairAddressGenerator
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
        description=Description(
            output="Liên hệ <contact_name> <contact_phone> tại {ADDRESS_PLACEHOLDER}"
        ),
        quality_score=0.9,
    )
    generator = PairAddressGenerator(
        nearby_service=None,
        project_service=None,
        chat_model=_StubChat(content, {"input_tokens": 11, "output_tokens": 22}),
        settings=settings,
    )
    app.dependency_overrides[get_pair_address_generator] = lambda: generator
    return app


def _body():
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
        "new_city": "TP.HCM",
        "new_ward": "Phường Bến Nghé",
        "new_display_address": "123 Đường Nguyễn Huệ, TP.HCM",
        "display_address": "123 Đường Lê Lợi, Quận 1, TP.HCM",
    }


async def test_pair_address_happy_path():
    app = _app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description/pair_address",
            params={"user_id": "u1", "listing_id": "l1", "style": "simple"},
            json=_body(),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["title"] == "Bán nhà Q1"
    assert "Anh A" in body["data"]["description"]
    assert "{ADDRESS_PLACEHOLDER}" not in body["data"]["description"]
    assert "Nguyễn Huệ" in body["data"]["description"]
    assert body["data"]["usage"]["used_requests"] == 1
