"""Weighted template selection (ported from bds-genai-dgl
core/generator/api/v1/description.py::select_template/_calculate_weight).

Behavior-frozen, made synchronous (the legacy ``asyncio.gather`` over a trivial
coroutine added nothing). One defensive guard added: if every candidate is
maxed out (total weight 0) fall back to a uniform random choice instead of the
legacy divide-by-zero.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence

from app.core.config import Settings
from app.modules.business.listing.models import Listing
from app.modules.business.listing.types import (
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
    TemplateResponse,
)

TemplateId = ProfessionalTemplateType | SimpleTemplateType | str | None


def _templates_for_style(
    style: StyleType,
) -> list[ProfessionalTemplateType] | list[SimpleTemplateType]:
    if style == StyleType.PROFESSIONAL:
        return list(ProfessionalTemplateType)
    if style == StyleType.SIMPLE:
        return list(SimpleTemplateType)
    raise ValueError(f"Invalid style: {style}")


def calculate_weight(
    template: ProfessionalTemplateType | SimpleTemplateType,
    usage: Counter,
    last_used: list,
    settings: Settings,
) -> tuple[str, float]:
    template_value: str = template.value
    usage_count = usage.get(template_value, 0)
    if usage_count >= settings.MAX_TEMPLATE_USAGE:
        return template_value, 0.0
    if usage_count == 1 and template_value in last_used:
        return template_value, settings.PROB_PENALTY
    return template_value, 1.0


def select_template_from_ids(
    template_ids: Sequence[TemplateId],
    style: StyleType,
    settings: Settings,
) -> TemplateResponse:
    templates = _templates_for_style(style)

    if len(templates) == 1:
        return TemplateResponse(selected_template=templates[0])

    if not template_ids or template_ids[0] is None:
        return TemplateResponse(selected_template=random.choice(templates))

    template_usage = Counter(template_ids)
    last_used = [template for template, _ in template_usage.most_common(2)]

    weighted = [
        calculate_weight(template, template_usage, last_used, settings)
        for template in templates
    ]
    values, weights = zip(*weighted, strict=False)
    total = sum(weights)
    if total == 0:
        return TemplateResponse(selected_template=random.choice(templates))
    normalized = [weight / total for weight in weights]
    selected = random.choices(values, weights=normalized, k=1)[0]
    return TemplateResponse(selected_template=selected)


def select_template(
    listings: list[Listing],
    style: StyleType,
    settings: Settings,
) -> TemplateResponse:
    return select_template_from_ids(
        [listing.template_id for listing in listings],
        style,
        settings,
    )
