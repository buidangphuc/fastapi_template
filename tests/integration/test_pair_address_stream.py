from httpx import ASGITransport, AsyncClient

from app.bootstrap.application import create_app
from app.bootstrap.services import LISTING_SERVICE_NAME, build_listing_runtime
from app.modules.platform.quota.factory import build_quota_service
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


class _Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


class _StreamingStubChat:
    """Stub chat model exposing ``astream`` (the free-form path under test)."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    async def astream(self, messages, config=None):
        for chunk in self._chunks:
            yield _Chunk(chunk)


class _StubHttpClient:
    async def request(self, *args, **kwargs):
        raise AssertionError("HTTP client should not be used in this test")

    async def aclose(self):
        return None


def _app(chunks: list[str], gemini_chunks: list[str] | None = None):
    settings = build_test_settings(
        MONGO_ENABLED=True,
        QUOTA_ENABLED=True,
        QUOTA_BACKEND="mongo",
        GMAP_PG_ENABLE=False,
        PROJECT_ENABLE=False,
        VERTEX_ENABLED=False,
        CHAT_MODEL="openai:gpt-4o-mini",
    )
    app = create_app(settings=settings, init_resources=False)
    app.state.resources.mongo = FakeMongoGateway()
    app.state.resources.quota = build_quota_service(
        app.state.settings,
        mongo=app.state.resources.mongo,
    )
    app.state.resources.services[LISTING_SERVICE_NAME] = build_listing_runtime(
        settings=app.state.settings,
        mongo=app.state.resources.mongo,
        quota=app.state.resources.quota,
        http_client=_StubHttpClient(),
        chat_model=_StreamingStubChat(chunks),
        # Inject a stub Gemini model (no real Vertex dep/creds) so the /gemini
        # endpoint is wired without VERTEX_ENABLED.
        gemini_chat_model=(
            _StreamingStubChat(gemini_chunks) if gemini_chunks is not None else None
        ),
    )
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


async def test_stream_splits_on_desc_marker_and_substitutes():
    # "Tiêu đề:" label stripped; "Mô tả:" marks the description boundary and is
    # consumed. Placeholders split across chunks exercise the hold-back.
    chunks = [
        "Tiêu đề: Bán nhà Q1\n",
        "Mô tả: Liên hệ <contact_name> ",
        "<contact_phone> tại {ADDRESS_PLA",
        "CEHOLDER}.",
    ]
    app = _app(chunks)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description/pair_address/stream",
            params={"user_id": "u1", "style": "simple"},
            json=_body(),
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text

    # Title and description arrive as separate, parseable fields.
    assert '"type": "title"' in text
    assert "Bán nhà Q1" in text
    assert '"type": "description"' in text
    # Labels are consumed/stripped, not leaked into the output.
    assert "Tiêu đề:" not in text
    assert "Mô tả:" not in text
    # Placeholders substituted (even when split across chunks).
    assert "Anh A" in text  # <contact_name>
    assert "0900" in text  # <contact_phone>
    assert "Nguyễn Huệ" in text  # {ADDRESS_PLACEHOLDER} -> new display address
    assert "<contact_name>" not in text
    assert "<contact_phone>" not in text
    assert "{ADDRESS_PLACEHOLDER}" not in text
    assert '"type": "done"' in text


async def test_stream_emits_done_on_empty_stream():
    app = _app([])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description/pair_address/stream",
            params={"user_id": "u2", "style": "simple"},
            json=_body(),
        )

    assert response.status_code == 200
    assert '"type": "done"' in response.text


async def test_stream_gemini_when_configured():
    app = _app([], gemini_chunks=["Tiêu đề Gemini", "\n\nMô tả <contact_name>."])
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description/pair_address/stream/gemini",
            params={"user_id": "g1", "style": "simple"},
            json=_body(),
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    assert '"type": "title"' in text
    assert "Tiêu đề Gemini" in text
    assert "Anh A" in text  # <contact_name> substituted
    assert "<contact_name>" not in text
    assert '"type": "done"' in text


async def test_stream_gemini_501_when_not_configured():
    app = _app([])  # no gemini model injected, VERTEX_ENABLED off
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/description/pair_address/stream/gemini",
            params={"user_id": "g2", "style": "simple"},
            json=_body(),
        )

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "vertex_not_configured"
