"""DGL listing-generator domain settings (usage quota).

Ported from bds-genai-dgl ``common/setting.py``. ``MAX_RESET_LIMIT_DAYS`` is
mutated at runtime by the legacy ``PUT /day_limit`` endpoint (process-local,
non-persistent — matches legacy behavior; a known limitation parked for later).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ListingSettingsMixin(BaseModel):
    MAX_USAGE_LIMIT_PER_USER: int = Field(default=100, gt=0)
    MAX_RESET_LIMIT_DAYS: int = Field(default=30, gt=0)
    # Template-selection weighting (legacy MAX_TEMPLATE_USAGE / PROB_PENALTY).
    MAX_TEMPLATE_USAGE: int = Field(default=2, gt=0)
    PROB_PENALTY: float = Field(default=0.3, ge=0)
