from types import SimpleNamespace

from app.modules.business.listing.generation.description import (
    Content,
    Description,
    Title,
)
from app.modules.business.listing.generation.pair_address import PairAddressGenerator
from app.modules.business.listing.schemas import PairAddressParams
from app.modules.business.listing.types import (
    AddressVersionType,
    LanguageType,
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


class _StubChat:
    def __init__(self, content: Content, usage: dict) -> None:
        self._content = content
        self._usage = usage

    def with_structured_output(self, schema, include_raw: bool = False):
        return _StubStructured(self._content, self._usage)


def _generator(content: Content, usage: dict):
    settings = build_test_settings(
        GMAP_PG_ENABLE=False, PROJECT_ENABLE=False, CHAT_MODEL="openai:gpt-4o-mini"
    )
    return PairAddressGenerator(
        nearby_service=None,
        project_service=None,
        chat_model=_StubChat(content, usage),
        settings=settings,
    )


def _params(**overrides) -> PairAddressParams:
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
        "new_city": "TP.HCM",
        "new_ward": "Phường Bến Nghé",
        "new_display_address": "123 Đường Nguyễn Huệ, Phường Bến Nghé, TP.HCM",
        "display_address": "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM",
    }
    base.update(overrides)
    return PairAddressParams(**base)


def test_normalize_address_prefixes_lowercases():
    out = PairAddressGenerator._normalize_address_prefixes(
        "Đường Lê Lợi, Phường Bến Nghé, Quận 1"
    )
    assert out == "đường Lê Lợi, phường Bến Nghé, quận 1"


def test_replace_placeholder_combines_new_and_old():
    content = "Nhà đẹp tại {ADDRESS_PLACEHOLDER}, giá tốt"
    out = PairAddressGenerator._replace_address_placeholders(content, _params())
    assert "{ADDRESS_PLACEHOLDER}" not in out
    assert "Nguyễn Huệ" in out  # new address present
    # All variations embed the truncated old address (district+city); "cũ" is
    # absent from one variation ("trước đây ..."), so assert the old part itself.
    assert "quận 1" in out


def test_replace_placeholder_new_only():
    params = _params(display_address=None)
    out = PairAddressGenerator._replace_address_placeholders(
        "tại {ADDRESS_PLACEHOLDER}", params
    )
    assert "Nguyễn Huệ" in out
    assert "{ADDRESS_PLACEHOLDER}" not in out


def test_build_fallback_title_under_limit():
    title = PairAddressGenerator._build_fallback_title(
        _params(),
        {"formatted_price": "2 tỷ", "formatted_area": "50 m2"},
        AddressVersionType.OLD,
    )
    assert len(title) <= 99
    assert "bán" in title
    assert "nhà" in title


async def test_agenerate_replaces_placeholder_and_inserts_contact():
    content = Content(
        title=Title(output="Bán nhà Q1"),
        description=Description(
            output="Liên hệ <contact_name> <contact_phone> tại {ADDRESS_PLACEHOLDER}"
        ),
        quality_score=0.9,
    )
    generator = _generator(content, {"input_tokens": 11, "output_tokens": 22})
    result = await generator.agenerate(
        language=LanguageType.VI,
        tone=ToneType.SIMPLE,
        style=StyleType.SIMPLE,
        params=_params(),
        template_id=SimpleTemplateType.TEMPLATE1,
        address_version=AddressVersionType.NEW,
    )
    assert "Anh A" in result["description"]
    assert "{ADDRESS_PLACEHOLDER}" not in result["description"]
    assert "Nguyễn Huệ" in result["description"]
    assert result["tokens"]["usage"]["completion_tokens"] == 22
    assert result["prompt_version"] == "listing-pair-address-2026-06-02"


async def test_agenerate_falls_back_when_title_too_long():
    content = Content(
        title=Title(output="x" * 150),
        description=Description(output="mô tả"),
        quality_score=0.5,
    )
    generator = _generator(content, {})
    result = await generator.agenerate(
        language=LanguageType.VI,
        tone=ToneType.SIMPLE,
        style=StyleType.SIMPLE,
        params=_params(),
        template_id=SimpleTemplateType.TEMPLATE1,
    )
    assert len(result["title"]) <= 99
    assert result["title"] != "x" * 150
    assert "bán" in result["title"]
