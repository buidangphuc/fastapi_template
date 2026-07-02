import pytest

from app.modules.business.listing.services.template_selection import (
    ListingTemplateSelectionService,
)
from app.modules.business.listing.types import (
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
)
from tests.factories import build_test_settings


class _NoReadStore:
    async def get_recent_ai_template_ids(self, *args, **kwargs):
        raise AssertionError("simple style should not read listing history")


class _TemplateHistoryStore:
    async def get_recent_ai_template_ids(self, *args, **kwargs):
        return [
            ProfessionalTemplateType.TEMPLATE1,
            ProfessionalTemplateType.TEMPLATE1,
        ]


@pytest.mark.parametrize("style", [StyleType.SIMPLE, "simple"])
async def test_simple_style_returns_template_without_reading_history(style):
    service = ListingTemplateSelectionService(_NoReadStore(), build_test_settings())

    result = await service.select("u1", style)

    assert result.selected_template == SimpleTemplateType.TEMPLATE1


async def test_professional_style_uses_recent_template_ids():
    service = ListingTemplateSelectionService(
        _TemplateHistoryStore(),
        build_test_settings(),
    )

    result = await service.select("u1", StyleType.PROFESSIONAL)

    assert result.selected_template != ProfessionalTemplateType.TEMPLATE1
