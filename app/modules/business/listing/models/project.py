"""Cached BDS project-summary Mongo document model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: str
    summary: str | None = None
    investor: str | None = None
    location: str | None = None
    design: str | None = None
    utility: str | None = None
    legal: str | None = None
