import json
from types import SimpleNamespace

import httpx

from app.modules.business.listing.models import Project
from app.modules.business.listing.prompt_provider import FilePromptProvider
from app.modules.business.listing.services.project import ProjectService
from tests.factories import build_test_settings
from tests.mongo_fake import FakeMongoGateway


class _StubChat:
    def __init__(self, content: str) -> None:
        self.content = content

    async def ainvoke(self, messages, **kwargs):
        return SimpleNamespace(content=self.content)


class _BoomChat:
    async def ainvoke(self, messages, **kwargs):
        raise AssertionError("LLM must not be called on cache hit")


def _project_handler(detail_info: str = "Dự án ABC"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"projectId": 1, "detailInfo": detail_info})

    return handler


def _service(handler, chat, mongo=None):
    settings = build_test_settings()
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://bds"
    )
    mongo = mongo or FakeMongoGateway()
    service = ProjectService(client, chat, mongo, settings, FilePromptProvider())
    return service, mongo, settings


async def test_get_summary_none_without_project_id():
    service, _, _ = _service(_project_handler(), _StubChat("{}"))
    assert await service.get_summary(None) is None
    assert await service.get_summary("") is None


async def test_generate_summary_calls_llm_and_caches():
    summary = json.dumps(
        {
            "Chủ đầu tư": "XYZ",
            "Vị trí": "Q1",
            "Thiết Kế - Mặt Bằng": "3PN",
            "Tiện ích": "hồ bơi",
            "Pháp lý": "sổ đỏ",
        },
        ensure_ascii=False,
    )
    service, mongo, settings = _service(_project_handler(), _StubChat(summary))
    project = await service.get_summary("123")
    assert isinstance(project, Project)
    assert project.investor == "XYZ"
    assert project.location == "Q1"
    cached = await mongo.collection(settings.MONGODB_PROJECT_COLLECTION).find_one(
        {"project_id": "123"}
    )
    assert cached is not None


async def test_get_summary_returns_cache_without_llm():
    mongo = FakeMongoGateway()
    settings = build_test_settings()
    await mongo.collection(settings.MONGODB_PROJECT_COLLECTION).insert_one(
        {
            "project_id": "p1",
            "summary": "cached",
            "investor": "INV",
            "location": "L",
            "design": "D",
            "utility": "U",
            "legal": "LE",
        }
    )
    service, _, _ = _service(lambda r: httpx.Response(404), _BoomChat(), mongo=mongo)
    project = await service.get_summary("p1")
    assert project is not None
    assert project.summary == "cached"
    assert project.investor == "INV"


async def test_generate_summary_none_when_no_detail_info():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"projectId": 1, "detailInfo": None})

    service, _, _ = _service(handler, _StubChat("{}"))
    assert await service.get_summary("404") is None
