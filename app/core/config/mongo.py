"""MongoDB settings.

Platform Mongo runtime settings (URI / database / timeouts) plus the DGL
listing-generator collection names. Disabled by default — the platform core runs
on Postgres + Redis; the DGL migration enables this to reuse the existing Mongo
collections (submitted listings, project-summary cache). See docs/adr/0001 (D2).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MongoSettingsMixin(BaseModel):
    MONGO_ENABLED: bool = True
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "app"
    MONGODB_CONNECT_TIMEOUT_MS: int = Field(default=10_000, gt=0)
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = Field(default=10_000, gt=0)
    # DGL listing-generator domain collections.
    MONGODB_USAGE_COLLECTION: str = "user"
    MONGODB_SUBMIT_COLLECTION: str = "submit"
    MONGODB_PROJECT_COLLECTION: str = "project"
