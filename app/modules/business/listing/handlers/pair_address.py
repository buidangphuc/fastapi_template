"""Pair-address description generator (ported from bds-genai-dgl
core/generator/service/pair_address.py).

Shares prompt building with the description generator via the ``prompts``
module (``address_placeholder=True`` opening + address-derived title options).
Pair-address specifics owned here: ``{ADDRESS_PLACEHOLDER}`` post-processing,
address-prefix normalization, ``address_for_title`` selection, and a title-
length retry that falls back to a deterministic title.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import numpy as np
from loguru import logger

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
from app.modules.business.listing.handlers.description import Content
from app.modules.business.listing.prompt import (
    OpenAIPromptTemplate,
    PromptSectionTemplate,
)
from app.modules.business.listing.schemas import PairAddressParams

_ADDRESS_PREFIX_RE = re.compile(
    r"(?<![\w])(Đường|Phố|Phường|Quận|Huyện|Xã|Tỉnh|Thành phố|Thị xã|Thị trấn)(?=[\s,]|$)",
    re.UNICODE,
)
_MAX_TITLE_LENGTH = 99
_MAX_TITLE_ATTEMPTS = 2


class PairAddressGenerator:
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

    async def get_nearby(self, params: PairAddressParams) -> dict[str, list[str]]:
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
        nearby_places = await self._nearby.search(
            place,
            params.lat,
            params.lng,
            nearby_types=nearby_types,
            radius=self._settings.GMAP_PG_RADIUS,
            language=self._settings.GMAP_PG_LANGUAGE_VI,
            rankby=self._settings.GMAP_PG_NEARBY_RANKBY,
        )
        return nearby_places or {}

    async def get_project(self, params: PairAddressParams) -> Any:
        return await self._project.get_summary(project_id=params.project_id)

    async def _gather_context(self, params: PairAddressParams) -> tuple[dict, Any]:
        nearby_places: dict = {}
        project = None
        semaphore = asyncio.Semaphore(self._settings.GMAP_PG_CONCURRENCY)

        async def _run(name: str, coro: Any) -> tuple[str, Any]:
            async with semaphore:
                try:
                    return name, await coro
                except Exception:
                    logger.warning("[%s] async task failed, skipping", name)
                    return name, None

        tasks = []
        if self._settings.GMAP_PG_ENABLE:
            tasks.append(asyncio.create_task(_run("nearby", self.get_nearby(params))))
        if self._settings.PROJECT_ENABLE:
            tasks.append(asyncio.create_task(_run("project", self.get_project(params))))

        if tasks:
            try:
                for task in asyncio.as_completed(
                    tasks, timeout=self._settings.ASYNC_TASK_TIMEOUT
                ):
                    name, value = await task
                    if name == "nearby":
                        nearby_places = value or {}
                    elif name == "project":
                        project = value
            except TimeoutError:
                logger.warning("Async task timeout; proceeding with available data")
        return nearby_places, project

    @staticmethod
    def _normalize_address_prefixes(address: str | None) -> str | None:
        if not address:
            return address
        return _ADDRESS_PREFIX_RE.sub(lambda m: m.group(0).lower(), address)

    @classmethod
    def _replace_address_placeholders(
        cls, content: str, params: PairAddressParams
    ) -> str:
        if not content:
            return content

        new_address = cls._normalize_address_prefixes(
            getattr(params, "new_display_address", None)
        )
        old_address = cls._normalize_address_prefixes(
            getattr(params, "display_address", None)
        )

        truncated_old_address = old_address
        if old_address:
            address_parts = [part.strip() for part in old_address.split(",")]
            if len(address_parts) >= 2:
                truncated_old_address = ", ".join(address_parts[-2:])

        if not new_address and not truncated_old_address:
            return content
        if new_address and not truncated_old_address:
            formatted_address = new_address
        elif truncated_old_address and not new_address:
            formatted_address = truncated_old_address
        else:
            variations = [
                f"{new_address} ({truncated_old_address} cũ)",
                f"{new_address} (cũ: {truncated_old_address})",
                f"{new_address}, trước đây {truncated_old_address}",
                f"{new_address} - {truncated_old_address} cũ",
                f"{new_address} (địa chỉ cũ: {truncated_old_address})",
            ]
            formatted_address = str(np.random.choice(variations))

        return content.replace("{ADDRESS_PLACEHOLDER}", formatted_address)

    @classmethod
    def _build_fallback_title(
        cls,
        params: PairAddressParams,
        params_dict: dict[str, Any],
        address_version: AddressVersionType,
        max_length: int = _MAX_TITLE_LENGTH,
    ) -> str:
        goal = (params.goal or "bán").strip()
        property_type = (params.property_type or "BĐS").strip()
        price = (params_dict.get("formatted_price") or "").strip()
        area = (params_dict.get("formatted_area") or "").strip()
        detail = ", ".join(bit for bit in [area, price] if bit)

        if address_version == AddressVersionType.NEW:
            address_attrs = ("new_ward", "new_city")
        else:
            address_attrs = ("district", "ward", "city")

        location_candidates: list[str] = []
        for attr in address_attrs:
            val = getattr(params, attr, None)
            if val and val.strip():
                normalized = cls._normalize_address_prefixes(val.strip())
                if normalized:
                    location_candidates.append(normalized)

        location = (
            str(np.random.choice(location_candidates)) if location_candidates else ""
        )
        location_suffix = f" tại {location}" if location else ""

        samples = [
            f"{goal} {property_type} {detail}{location_suffix}",
            f"{goal} gấp {property_type} {detail}{location_suffix}",
            f"{property_type} {detail}{location_suffix}, {goal}",
        ]
        candidate = str(np.random.choice(samples))
        candidate = re.sub(r"\s+", " ", candidate).strip()
        candidate = candidate.replace(" ,", ",").replace(",,", ",").strip(", .")
        if len(candidate) > max_length:
            return candidate[:max_length].rstrip(", .")
        return candidate

    @staticmethod
    def _title_component_options(address_for_title: str) -> list[str]:
        if not address_for_title:
            return [
                "- USE city and specific location from the address in the title.",
                "- USE ward and city from the address in the title.",
                "- USE key parts of the address to keep title under 99 characters.",
            ]
        parts = [p.strip() for p in address_for_title.split(",")]
        if len(parts) >= 3:
            location, ward, city = parts[0], parts[1], parts[2]
            return [
                f'- USE city and specific location in the title. e.g: "{location}, {city}"',
                f'- USE ward and city in the title. e.g: "{ward}, {city}"',
                f'- USE ward, district, and city in the title. e.g: "{ward}, {city}"',
                "- USE key parts of the address to keep title under 99 characters",
            ]
        if len(parts) >= 2:
            location, city = parts[0], parts[1]
            return [
                f'- USE location and city in the title. e.g: "{location}, {city}"',
                "- USE key parts of the address to keep title under 99 characters",
            ]
        return ["- USE key parts of the address to keep title under 99 characters"]

    async def agenerate(
        self,
        *,
        language: LanguageType,
        tone: ToneType,
        style: StyleType,
        params: PairAddressParams,
        template_id: ProfessionalTemplateType | SimpleTemplateType,
        address_version: AddressVersionType = AddressVersionType.OLD,
    ) -> dict[str, Any]:
        start_t = time.time()
        nearby_places, project = await self._gather_context(params)

        params_dict = params.model_dump()
        params_dict.pop("lat", None)
        params_dict.pop("lng", None)
        prompts.apply_price_area_formatting(params_dict)

        def build_address_parts(keys: list[str]) -> list[str]:
            return [
                f"{params_dict[key]}"
                for key in keys
                if key in params_dict and params_dict[key] not in (None, "")
            ]

        new_address_parts = build_address_parts(["new_street", "new_ward", "new_city"])
        old_address_parts = build_address_parts(["street", "ward", "district", "city"])

        if address_version == AddressVersionType.NEW:
            if params_dict.get("new_display_address"):
                params_dict["address_for_title"] = params_dict["new_display_address"]
            elif new_address_parts:
                params_dict["address_for_title"] = ",".join(new_address_parts)
            else:
                params_dict["address_for_title"] = ",".join(old_address_parts)
        elif params_dict.get("display_address"):
            params_dict["address_for_title"] = params_dict["display_address"]
        else:
            params_dict["address_for_title"] = ",".join(old_address_parts)

        params_dict["address_for_title"] = self._normalize_address_prefixes(
            params_dict["address_for_title"]
        )

        for key in [
            "price",
            "price_unit",
            "area",
            "area_unit",
            "street",
            "ward",
            "district",
            "city",
            "new_street",
            "new_ward",
            "new_city",
            "address",
            "address_version",
            "contact_phone",
            "contact_name",
            "contact_email",
            "new_display_address",
            "display_address",
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
                params,
                hook_str,
                self._title_component_options(params_dict.get("address_for_title", "")),
            )
        )
        prompts.add_description_sections(
            content_structure, style, template_id, params, address_placeholder=True
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

        ignore = {
            "is_price_available",
            "platform",
            "new_city",
            "new_street",
            "new_ward",
            "lat",
            "lng",
            "formatted_address",
            "formatted_address_title",
        }
        for key, value in params_dict.copy().items():
            if (
                not value
                or (isinstance(value, int | float) and value <= 0)
                or key in ignore
            ):
                params_dict.pop(key)

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
        content_out: Content | None = None
        raw = None
        title_ok = False
        for attempt in range(_MAX_TITLE_ATTEMPTS):
            result = await structured.ainvoke(
                prompt.to_api_message(), config=self._trace_config
            )
            content_out = result["parsed"]
            raw = result.get("raw")
            if len(content_out.get_title()) <= _MAX_TITLE_LENGTH:
                title_ok = True
                break
            logger.warning(
                "Title too long, retrying (%d/%d)", attempt + 1, _MAX_TITLE_ATTEMPTS
            )

        if not title_ok and content_out is not None:
            content_out.title.output = self._build_fallback_title(
                params, params_dict, address_version
            )

        content_out.insert_contact(
            contact_name=params.contact_name,
            contact_phone=params.contact_phone,
        )
        title_processed = self._replace_address_placeholders(
            content_out.get_title(), params
        )
        description_processed = self._replace_address_placeholders(
            content_out.get_description(), params
        )

        usage = getattr(raw, "usage_metadata", None) or {}
        end_t = time.time()
        return {
            "prompt": prompt.to_str(),
            "title": title_processed,
            "description": description_processed,
            "tokens": {
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                }
            },
            "title_length": len(title_processed),
            "description_length": len(description_processed),
            "generating_time": end_t - start_t,
            "llm_model_name": self._settings.CHAT_MODEL,
        }
