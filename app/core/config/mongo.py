"""MongoDB connection settings (DGL listing-generator domain store).

Disabled by default: the platform core runs on Postgres + Redis. The DGL
migration enables this to reuse the existing Mongo collections (usage quotas,
submitted listings, project-summary cache). See docs/adr/0001 (D2).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MongoSettingsMixin(BaseModel):
    MONGO_ENABLED: bool = False
    MONGODB_URI: str = ""
    MONGODB_DATABASE: str = "genai"
    MONGODB_CONNECTION_TIMEOUT_MS: int = Field(default=2000, gt=0)
    MONGODB_USAGE_COLLECTION: str = "user"
    MONGODB_SUBMIT_COLLECTION: str = "submit"
    MONGODB_PROJECT_COLLECTION: str = "project"
