"""Submitted-listing Mongo document model."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from app.modules.business.listing.types import (
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
    prompt_version: str | None = None

    @field_serializer("created_date", when_used="json")
    def _serialize_created_date(self, value: datetime) -> str:
        return value.strftime(DATETIME_FORMAT)
