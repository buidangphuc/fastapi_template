"""Description generator (ported from bds-genai-dgl
core/generator/service/description.py).

Prompt sections are built by the shared ``prompts`` module; this class owns the
description-specific bits: context gathering, address formatting, the ignored-
params rule, and the LLM call via ``ai/llm`` ``with_structured_output(Content)``
(token usage mapped back to the legacy ``tokens.usage.*`` shape).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.modules.business.listing import prompt_builders as prompts
from app.modules.business.listing.config import (
    AddressVersionType,
    LanguageType,
    ParamLangMap,
    ProfessionalTemplateType,
    SimpleTemplateType,
    StyleType,
    ToneType,
)
from app.modules.business.listing.prompt import (
    OpenAIPromptTemplate,
    PromptSectionTemplate,
)
from app.modules.business.listing.schemas import AllParams


class Title(BaseModel):
    output: str = Field(..., description="Generated Title")


class Description(BaseModel):
    output: str = Field(..., description="Generated Description")


class Content(BaseModel):
    title: Title
    description: Description
    quality_score: float = Field(..., description="Quality Score (0-1)")

    def to_str(self) -> str:
        return f"{self.title.output}\n{self.description.output}"

    def get_title(self) -> str:
        return self.title.output.strip()

    def get_description(self) -> str:
        return self.description.output

    def insert_contact(self, contact_phone: str, contact_name: str) -> None:
        """Insert contact info into the ending to avoid PII leakage to the LLM."""
        self.description.output = self.description.output.replace(
            "<contact_phone>", contact_phone
        ).replace("<contact_name>", contact_name)


class DescriptionGenerator:
    def __init__(
        self,
        *,
        nearby_service: Any,
        project_service: Any,
        chat_model: Any,
        settings: Settings,
        trace_config: dict[str, Any] | None = None,
    ) -> None:
        self._nearby = nearby_service
        self._project = project_service
        self._chat_model = chat_model
        self._settings = settings
        self._trace_config = trace_config or {}

    async def get_nearby(
        self,
        params: AllParams,
        address_version: AddressVersionType = AddressVersionType.OLD,
    ) -> dict[str, list[str]] | None:
        if address_version == AddressVersionType.NEW:
            place = None  # location mapping dropped; NEW uses lat/lng only
            logger.info("NEW address: location mapping dropped; using lat/lng only")
        else:
            data = params.model_dump()
            parts = [
                data[key]
                for key in ("street", "ward", "district", "city")
                if data.get(key) not in (None, "")
            ]
            place = ",".join(parts)

        nearby_types = [
            t.strip()
            for t in self._settings.GMAP_PG_NEARBY_TYPES.split(",")
            if t.strip()
        ]
        return await self._nearby.search(
            place,
            params.lat,
            params.lng,
            nearby_types=nearby_types,
            radius=self._settings.GMAP_PG_RADIUS,
            language=self._settings.GMAP_PG_LANGUAGE_VI,
            rankby=self._settings.GMAP_PG_NEARBY_RANKBY,
        )

    async def get_project(self, params: AllParams) -> Any:
        return await self._project.get_summary(project_id=params.project_id)

    async def _gather_context(
        self, params: AllParams, address_version: AddressVersionType
    ) -> tuple[dict, Any]:
        nearby_places: dict = {}
        project = None
        semaphore = asyncio.Semaphore(self._settings.GMAP_PG_CONCURRENCY)

        async def _run(name: str, coro: Any) -> tuple[str, Any]:
            async with semaphore:
                return name, await coro

        tasks = []
        if self._settings.GMAP_PG_ENABLE:
            tasks.append(
                asyncio.create_task(
                    _run("nearby", self.get_nearby(params, address_version))
                )
            )
        if self._settings.PROJECT_ENABLE:
            tasks.append(asyncio.create_task(_run("project", self.get_project(params))))

        for task in asyncio.as_completed(
            tasks, timeout=self._settings.ASYNC_TASK_TIMEOUT
        ):
            name, value = await task
            if name == "nearby":
                nearby_places = value or {}
            elif name == "project":
                project = value
        return nearby_places, project

    async def agenerate(
        self,
        *,
        language: LanguageType,
        tone: ToneType,
        style: StyleType,
        params: AllParams,
        template_id: ProfessionalTemplateType | SimpleTemplateType,
        address_version: AddressVersionType = AddressVersionType.OLD,
    ) -> dict[str, Any]:
        start_t = time.time()
        nearby_places, project = await self._gather_context(params, address_version)

        params_dict = params.model_dump()
        params_dict.pop("lat", None)
        params_dict.pop("lng", None)
        prompts.apply_price_area_formatting(params_dict)

        formatted_address = [
            f"{params_dict[key]}"
            for key in ["street", "ward", "district", "city"]
            if key in params_dict and params_dict[key] not in (None, "")
        ]
        params_dict["formatted_address"] = ",".join(formatted_address)

        for key in [
            "price",
            "price_unit",
            "area",
            "area_unit",
            "street",
            "ward",
            "district",
            "city",
            "contact_phone",
            "contact_name",
            "contact_email",
        ]:
            params_dict.pop(key, None)

        prompt = OpenAIPromptTemplate(model_name=self._settings.CHAT_MODEL)
        prompts.add_role_and_tone(prompt, params, tone)
        rules = prompts.build_rules(params, params_dict)
        hook_str = prompts.pick_hook_str(
            params_dict, style, self._settings.MAX_HOOK_WORDS
        )

        content_structure = PromptSectionTemplate(name="#Content Structure")
        content_structure.add_section(
            prompts.build_title_section(
                params, hook_str, prompts.DESCRIPTION_ADDRESS_OPTIONS
            )
        )
        prompts.add_description_sections(
            content_structure, style, template_id, params, address_placeholder=False
        )
        nearby_section, nearby_input = prompts.build_nearby_section(
            nearby_places, self._settings
        )
        if nearby_section is not None:
            content_structure.add_section(nearby_section)
        project_section, project_input = prompts.build_project_section(project)
        if project_section is not None:
            content_structure.add_section(project_section)
        content_structure.add_section(prompts.build_ending_section())
        prompt.add_section(content_structure)

        ignored = []
        for key, value in params_dict.copy().items():
            if not value or (isinstance(value, int | float) and value <= 0):
                params_dict.pop(key)
                ignored.append(key)
        ignored.extend(["lat", "lng", "is_price_available"])
        ignore_str = ", ".join(str(ParamLangMap.get(key)) for key in ignored)
        rules.add_content(f"DO NOT include {ignore_str} in the content.")

        _params_str = ",".join(
            f"{ParamLangMap.get(key)}:{value}" for key, value in params_dict.items()
        )
        if self._settings.GMAP_PG_ENABLE and nearby_places:
            _params_str = _params_str + "," + nearby_input
        if self._settings.PROJECT_ENABLE and project:
            _params_str = _params_str + "," + project_input

        prompt.add_section(PromptSectionTemplate(name="#Input", contents=[_params_str]))
        prompt.add_section(rules)
        prompt.add_variables(params_dict)

        structured = self._chat_model.with_structured_output(Content, include_raw=True)
        result = await structured.ainvoke(
            prompt.to_api_message(), config=self._trace_config
        )
        content_out: Content = result["parsed"]
        raw = result.get("raw")
        content_out.insert_contact(
            contact_name=params.contact_name,
            contact_phone=params.contact_phone,
        )

        usage = getattr(raw, "usage_metadata", None) or {}
        end_t = time.time()
        return {
            "prompt": prompt.to_str(),
            "title": content_out.get_title(),
            "description": content_out.get_description(),
            "tokens": {
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                }
            },
            "title_length": len(content_out.get_title()),
            "description_length": len(content_out.get_description()),
            "generating_time": end_t - start_t,
            "llm_model_name": self._settings.CHAT_MODEL,
        }
