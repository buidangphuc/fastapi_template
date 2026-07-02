from types import SimpleNamespace

import pytest

from app.modules.business.listing.generation.description import (
    Content,
    Description,
    DescriptionGenerator,
    Title,
)
from app.modules.business.listing.schemas import AllParams
from app.modules.business.listing.types import (
    LanguageType,
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
    ToneType,
)
from tests.factories import build_test_settings


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


class _StubChatModel:
    def __init__(self, content: Content, usage: dict) -> None:
        self._content = content
        self._usage = usage

    def with_structured_output(self, schema, include_raw: bool = False):
        return _StubStructured(self._content, self._usage)


def _generator(content: Content, usage: dict, **overrides):
    settings = build_test_settings(
        GMAP_PG_ENABLE=False,
        PROJECT_ENABLE=False,
        CHAT_MODEL="openai:gpt-4o-mini",
        **overrides,
    )
    return DescriptionGenerator(
        nearby_service=None,
        project_service=None,
        chat_model=_StubChatModel(content, usage),
        settings=settings,
    )


def _params(**overrides) -> AllParams:
    base = {
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
    base.update(overrides)
    return AllParams(**base)


async def test_agenerate_returns_parsed_and_inserts_contact():
    content = Content(
        title=Title(output="Bán nhà Q1"),
        description=Description(output="Liên hệ <contact_name> <contact_phone>"),
        quality_score=0.9,
    )
    generator = _generator(content, {"input_tokens": 11, "output_tokens": 22})
    result = await generator.agenerate(
        language=LanguageType.VI,
        tone=ToneType.SIMPLE,
        style=StyleType.SIMPLE,
        params=_params(),
        template_id=SimpleTemplateType.TEMPLATE1,
    )
    assert result["title"] == "Bán nhà Q1"
    assert "Anh A" in result["description"]
    assert "0900" in result["description"]
    assert "<contact_phone>" not in result["description"]
    assert result["tokens"]["usage"]["prompt_tokens"] == 11
    assert result["tokens"]["usage"]["completion_tokens"] == 22
    assert result["llm_model_name"] == "openai:gpt-4o-mini"
    assert result["prompt"]
    assert result["prompt_version"] == "listing-description-2026-06-02"


@pytest.mark.parametrize("template_id", list(ProfessionalTemplateType))
async def test_agenerate_professional_templates_build(template_id):
    content = Content(
        title=Title(output="t"),
        description=Description(output="d"),
        quality_score=0.5,
    )
    generator = _generator(content, {})
    result = await generator.agenerate(
        language=LanguageType.VI,
        tone=ToneType.PROFESSIONAL,
        style=StyleType.PROFESSIONAL,
        params=_params(),
        template_id=template_id,
    )
    assert result["title"] == "t"
    assert "#Role" in result["prompt"]
    assert "#Content Structure" in result["prompt"]


async def test_agenerate_negotiable_price():
    content = Content(
        title=Title(output="t"),
        description=Description(output="d"),
        quality_score=0.5,
    )
    generator = _generator(content, {})
    result = await generator.agenerate(
        language=LanguageType.VI,
        tone=ToneType.SIMPLE,
        style=StyleType.SIMPLE,
        params=_params(price=0.0, price_unit="Thoả thuận"),
        template_id=SimpleTemplateType.TEMPLATE1,
    )
    assert result["title"] == "t"
    assert result["tokens"]["usage"]["prompt_tokens"] == 0
