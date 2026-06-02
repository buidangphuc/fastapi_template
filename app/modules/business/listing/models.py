"""Mongo persistence document models.

Ported from bds-genai-dgl ``core/submit/model/listing.py`` and
``core/limiter/model/usage.py``. The legacy ``bson.ObjectId`` json_encoders are
dropped: we never read/write ``_id`` directly (Mongo assigns it; pydantic
ignores unknown keys on read). ``created_date`` is stored as a real datetime
(BSON date) and serialized to the legacy ``%Y-%m-%d %H:%M:%S`` string only in
JSON responses.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.modules.business.listing.config import (
    DATETIME_FORMAT,
    AuthorType,
    PlatformType,
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
)


class Listing(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str
    listing_id: str
    created_date: datetime
    style: StyleType | None = None
    prompt: str | None = None
    title: str
    description: str
    author: AuthorType
    version: str = ""
    platform: PlatformType | None = PlatformType.EMPTY
    template_id: ProfessionalTemplateType | SimpleTemplateType | None = None
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    generating_time: float | None = None
    llm_model_name: str | None = None
    user_input: str | None = None

    @field_serializer("created_date", when_used="json")
    def _serialize_created_date(self, value: datetime) -> str:
        return value.strftime(DATETIME_FORMAT)


class UsageUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: str
    used_requests: int
    first_request_date: datetime


class Project(BaseModel):
    """Cached project summary (ported from core/generator/model/project.py).

    Summary fields are optional (legacy required them, but the LLM may omit
    keys; the generator already filters out empty values)."""

    model_config = ConfigDict(populate_by_name=True)

    project_id: str
    summary: str | None = None
    investor: str | None = None
    location: str | None = None
    design: str | None = None
    utility: str | None = None
    legal: str | None = None
