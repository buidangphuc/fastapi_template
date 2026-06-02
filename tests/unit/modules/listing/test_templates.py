from collections import Counter
from datetime import datetime

from app.modules.business.listing.config import (
    DATETIME_FORMAT,
    AuthorType,
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
)
from app.modules.business.listing.models import Listing
from app.modules.business.listing.templates import calculate_weight, select_template
from tests.factories import build_test_settings


def _listing(template_id) -> Listing:
    return Listing(
        user_id="u1",
        listing_id="l1",
        title="t",
        description="d",
        author=AuthorType.AI,
        style=StyleType.PROFESSIONAL,
        template_id=template_id,
        created_date=datetime.now().strftime(DATETIME_FORMAT),
    )


def test_simple_style_returns_single_template():
    result = select_template([], StyleType.SIMPLE, build_test_settings())
    assert result.selected_template == SimpleTemplateType.TEMPLATE1


def test_professional_no_listings_returns_a_professional_template():
    result = select_template([], StyleType.PROFESSIONAL, build_test_settings())
    assert result.selected_template in set(ProfessionalTemplateType)


def test_calculate_weight_rules():
    settings = build_test_settings()  # MAX_TEMPLATE_USAGE=2, PROB_PENALTY=0.3
    template = ProfessionalTemplateType.TEMPLATE1
    _, maxed = calculate_weight(template, Counter({template.value: 2}), [], settings)
    assert maxed == 0.0
    _, penalized = calculate_weight(
        template, Counter({template.value: 1}), [template.value], settings
    )
    assert penalized == settings.PROB_PENALTY
    _, normal = calculate_weight(template, Counter(), [], settings)
    assert normal == 1.0


def test_maxed_template_never_selected():
    settings = build_test_settings()
    maxed = [
        _listing(ProfessionalTemplateType.TEMPLATE1)
        for _ in range(settings.MAX_TEMPLATE_USAGE)
    ]
    for _ in range(50):
        result = select_template(maxed, StyleType.PROFESSIONAL, settings)
        assert result.selected_template != ProfessionalTemplateType.TEMPLATE1
