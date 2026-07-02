"""DGL description-generator settings (Google Maps nearby, BDS project, LLM).

Ported from bds-genai-dgl ``common/setting.py``. The OpenAI sampling params are
renamed ``LISTING_LLM_*`` since generation now runs through the platform
``ai/llm`` layer; they are pinned on the chat model for behavior parity.
``GMAP_PG_NEARBY_TYPES`` is a CSV string (split in code) to match the platform's
CSV-setting convention.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratorSettingsMixin(BaseModel):
    # Google Maps (PropertyGuru proxy) nearby search.
    GMAP_PG_ENABLE: bool = True
    GMAP_PG_URL: str = "https://gmaps.integration.propertyguru.com"
    GMAP_PG_COOKIES: str = ""
    GMAP_PG_API_HEADER_REFERER: str = ""
    GMAP_PG_RADIUS: int = Field(default=2000, gt=0)
    GMAP_PG_LANGUAGE_VI: str = "vi"
    GMAP_PG_NEARBY_TYPES: str = "hospital,park,supermarket,school"
    GMAP_PG_NEARBY_KEEP_SCORE: float = Field(default=100, ge=0)
    GMAP_PG_SEARCH_TIMEOUT: int = Field(default=10, gt=0)
    GMAP_PG_CONCURRENCY: int = Field(default=5, gt=0)
    GMAP_PG_TOP_N_RESULTS: int = Field(default=3, gt=0)
    GMAP_PG_NEARBY_RANKBY: str = "prominence"
    ASYNC_TASK_TIMEOUT: int = Field(default=30, gt=0)

    # BDS project lookup + AI summary.
    PROJECT_ENABLE: bool = True
    BDS_PROJECT_URL: str = (
        "http://api.test.bds.lc/projectnet-service/api/Project/"
        "GetProjectDetail/ByLegacyId"
    )
    PROJECT_LLM_TEMPERATURE: float = Field(default=0.3, ge=0, le=2)

    # Listing description LLM sampling (legacy OPENAI_*), pinned for parity.
    LISTING_LLM_TEMPERATURE: float = Field(default=0.8, ge=0, le=2)
    LISTING_LLM_TOP_P: float = Field(default=1.0, ge=0, le=1)
    LISTING_LLM_PRESENCE_PENALTY: float = Field(default=0.0, ge=-2, le=2)
    LISTING_LLM_FREQUENCY_PENALTY: float = Field(default=0.0, ge=-2, le=2)
    MAX_HOOK_WORDS: int = Field(default=2, gt=0)
