"""BDS project lookup + AI summary, cached in Mongo.

Ported behavior-frozen from bds-genai-dgl ``core/generator/service/project.py``.
Structural changes: HTTP client + chat model + Mongo gateway are injected; the
summary LLM call runs through the platform ``ai/llm`` chat model (plain
completion → JSON) instead of the raw OpenAI client; the summary prompt is
loaded from a package asset (not ``os.getcwd()``).
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from loguru import logger
from pydantic import BaseModel

from app.core.config import Settings
from app.modules.business.listing.models import Project
from app.modules.platform.mongo.gateway import MongoGateway


class ProjectSearchResponse(BaseModel):
    projectId: int | None = None
    detailInfo: str | None = None


class ProjectService:
    def __init__(
        self,
        client: Any,
        chat_model: Any,
        mongo: MongoGateway,
        settings: Settings,
        prompt_provider: Any,
    ) -> None:
        self._client = client
        self._chat_model = chat_model
        self._projects = mongo.collection(settings.MONGODB_PROJECT_COLLECTION)
        self._settings = settings
        self._prompt_provider = prompt_provider
        self._locks: dict[Any, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def _search(self, legacy_id: Any) -> ProjectSearchResponse | None:
        try:
            response = await self._client.request(
                "GET",
                self._settings.BDS_PROJECT_URL,
                params={"legacyId": legacy_id},
                headers={"accept": "text/plain"},
            )
            if response.status_code == 301:
                new_url = response.headers.get("location")
                if new_url:
                    response = await self._client.request(
                        "GET", new_url, headers={"accept": "text/plain"}
                    )
            if response.status_code != 200:
                logger.error(f"ProjectSearch error: {response.text} - {legacy_id}")
                return None
            return ProjectSearchResponse(**response.json())
        except Exception as exc:
            logger.error(f"ProjectSearch error: {exc} - {legacy_id}")
            return None

    async def get_summary(self, project_id: str | None) -> Project | None:
        if not project_id:
            return None
        logger.info(f"Fetching project summary: {project_id}")
        cached = await self._projects.find_one({"project_id": project_id})
        if cached and cached.get("summary") is not None:
            logger.info(f"Retrieved existing summary for project_id {project_id}")
            return Project(**cached)
        logger.info(f"No existing summary, generating for project_id {project_id}")
        return await self.generate_summary(project_id)

    async def generate_summary(self, project_id: str) -> Project | None:
        async with self._locks[project_id]:
            try:
                detail = await self._search(project_id)
                if detail is None or detail.detailInfo is None:
                    logger.error(f"Project detail not found for {project_id}")
                    return None

                messages = [
                    {
                        "role": "system",
                        "content": self._prompt_provider.get("project_summary"),
                    },
                    {"role": "user", "content": detail.detailInfo},
                ]
                result = await self._chat_model.ainvoke(messages)
                content = getattr(result, "content", result)
                parsed = json.loads(content)
                data = {
                    "project_id": project_id,
                    "summary": content,
                    "investor": parsed.get("Chủ đầu tư"),
                    "location": parsed.get("Vị trí"),
                    "design": parsed.get("Thiết Kế - Mặt Bằng"),
                    "utility": parsed.get("Tiện ích"),
                    "legal": parsed.get("Pháp lý"),
                }
                await self._projects.insert_one(data)
                logger.info(f"Stored summary for project_id {project_id}")
                return Project(**data)
            except Exception as exc:
                logger.error(f"Failed to summarize project_id {project_id}: {exc}")
                return None
            finally:
                self._locks.pop(project_id, None)
