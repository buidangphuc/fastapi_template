"""Pair-address description generator (ported from bds-genai-dgl
core/generator/service/pair_address.py).

Same shape as the description generator, plus the old/new address pairing:
the LLM is told to emit a ``{ADDRESS_PLACEHOLDER}`` token, which post-processing
replaces with a combined "new (old cũ)" address; a title-length retry falls back
to a deterministic title. Prompt-building kept verbatim; LLM call routed through
``ai/llm`` ``with_structured_output(Content)`` (same schema as description).
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

import numpy as np
from loguru import logger

from app.core.config import Settings
from app.modules.business.listing.config import (
    AddressVersionType,
    GoalTypeVN,
    InteriorTypeVN,
    LanguageType,
    LegalityTypeVN,
    ParamLangMap,
    PriceVNUnitType,
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
from app.modules.business.listing.utils import (
    cvt_shorten_number,
    number_standardize,
    random_use,
    random_use_one_in_list,
)

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
        logger.info(f"Nearby places for '{place}': {nearby_places}")
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
        for key, val in params_dict.items():
            if isinstance(val, float) and key not in ["price", "area"]:
                params_dict[key] = number_standardize(val)

        params_dict["is_price_available"] = False
        if params_dict["price_unit"] == PriceVNUnitType.NEGOTIABLE:
            params_dict["formatted_price"] = "giá thỏa thuận"
        elif params_dict["price"] is not None and params_dict["price"] > 0:
            _price = cvt_shorten_number(params_dict["price"])
            if params_dict["price_unit"] == PriceVNUnitType.CURRENCY_VND:
                params_dict["formatted_price"] = f"{_price} {params_dict['price_unit']}"
            elif params_dict["price_unit"] == PriceVNUnitType.UNIT_M2:
                params_dict["price_unit"] = (
                    params_dict["price_unit"].replace("m²", "m2").replace("Giá", "")
                )
                params_dict["formatted_price"] = f"{_price} {params_dict['price_unit']}"
            params_dict["is_price_available"] = True
        else:
            params_dict["formatted_price"] = None

        if params_dict["area"] is not None and params_dict["area"] > 0:
            params_dict["formatted_area"] = (
                f"{number_standardize(params_dict['area'])} {params_dict['area_unit']}"
            )
        else:
            params_dict["formatted_area"] = None

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
        else:
            if params_dict.get("display_address"):
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

        prompt_template = OpenAIPromptTemplate(model_name=self._settings.CHAT_MODEL)
        prompt_template.add_section(
            PromptSectionTemplate(
                name="#Role",
                contents=[
                    "You are a real estate content expert. Your task is to create a "
                    "detailed Vietnamese real estate description using the provided "
                    f"template and guidelines for {params.goal} {params.property_type}. "
                    "Ensure all instructions are followed accurately."
                ],
            )
        )
        if tone == ToneType.SIMPLE:
            prompt_template.add_section(
                PromptSectionTemplate(
                    name="#Tone",
                    contents=[
                        "Write in a gen-Z style",
                        "Target users are young people, aged 18-30",
                        "Use slang if necessary and abbreviations when appropriate",
                        "Avoid using formal language such as 'tuyệt vời, hấp dẫn, "
                        "giá trị, khám khá, etc.'",
                        "Do not mention aliases or nicknames of target users",
                    ],
                )
            )
        elif tone == ToneType.PROFESSIONAL:
            prompt_template.add_section(
                PromptSectionTemplate(
                    name="#Tone",
                    contents=[
                        "Target users are all customers, aged 30-50",
                        "Write in a professional tone to attract potential buyers "
                        "or renters.",
                    ],
                )
            )

        rule_blocks = PromptSectionTemplate(
            name="#Rules",
            contents=[
                """
- Only use the provided information; do not add or invent details.
- Keep the tone approachable and straightforward; avoid technical or overly formal language.
- Maintain the address exactly as given, even if there are duplicates or missing components.
- Do not use unnecessary symbols or alter numerical values.
- MUST Use Vietnamese
- Use short forms for any price (e.g: 2,5 tỷ or 12,1 tỷ, 100 triệu, 8 triệu, etc. ) and area (e.g., 100m2)
- ONLY USE Informations provided in the #Input. Otherwise, the content will be super negative.
- DO NOT mention legal documents if goal is for rent.
- DO NOT use emoji, special characters.
- Ensure the content is EASY to SCAN and READ.
- Area must be in m2.
- DO NOT use any special characters such •, *, etc.
- DO NOT use Pronouns such as "bạn, tôi, chúng tôi, etc."
""",
                f"- Price unit must be '{params_dict['formatted_price']}'."
                if params_dict["is_price_available"]
                else "",
                random_use(
                    '- Use dashes "-" for headings and "+" for bullet points.',
                    weights=0.6,
                ),
                "- DO NOT highlight the benefits of price, just mention 'giá thỏa thuận'"
                if params.price_unit == PriceVNUnitType.NEGOTIABLE
                else "",
            ],
        )

        hooks = [
            "Hot!",
            "Chính chủ",
            "bán gấp or cho thuê gấp",
            "hàng hiếm tại",
            "chỉ với",
            "đẹp, nhiều tiện ích",
            "view đẹp",
            "uy tín",
            "giá tốt",
        ]
        if params_dict["is_price_available"]:
            hooks.extend(["giá cực chất", "giá siêu hời", "giá ưu đãi"])
        if style == StyleType.SIMPLE:
            hooks.extend(["hàng hot", "bao đẹp", "đẹp xuất sắc", "siêu hot"])
        elif style != StyleType.PROFESSIONAL:
            raise ValueError("Style not supported")
        hook_str = "\n".join(np.random.choice(hooks, self._settings.MAX_HOOK_WORDS))

        content_structure = PromptSectionTemplate(name="#Content Structure")
        title_blocks = PromptSectionTemplate(
            name="1. Title: Introduce the property and goal.",
            contents=[
                """
- Include the following: address, price, area, and other key property details.
- Rewrite the title with a hook to be very natural and engaging.
- Separate price and area with comma.
- Ensure less than 99 characters.
- DO NOT put '-' in the title.
- Ensure the address is complete and accurate with prefix "tại", or "ở"
- DO NOT PUT VND in the title.
"""
            ],
        )
        component_options = self._title_component_options(
            params_dict.get("address_for_title", "")
        )
        title_blocks.add_contents(
            [
                random_use(random_use_one_in_list(component_options), weights=0.8),
                random_use(
                    "- Write with engaging title to capture attention from potential "
                    f"buyers or renters, combining with the following hooks: {hook_str}",
                    weights=0.8,
                ),
                random_use(
                    """
- Use abbreviations for address if possible.
    - "đường Nguyễn Văn Linh, Phường Tân Phong, Quận 7, TP.HCM" -> "Nguyễn Văn Linh, Tân Phong, Quận 7, TP.HCM"
    - "đường Nguyễn Văn Linh, Phường Tân Phong, Quận 7, TP.HCM" -> "đ.Nguyễn Văn Linh, p.Tân Phong, Q.7, HCM"
""",
                    weights=1,
                ),
                random_use(
                    """
- Use abbreviations when appropriate, such as:
  - phòng ngủ: PN. e.g: "3PN"
  - phòng tắm: WC or VS. e.g: "2WC" or "2VS"
  - đầy đủ: full
""",
                    weights=1,
                ),
                random_use(f"- MUST include goal in Title: {params.goal}", weights=1),
                random_use("- Can use abbreviations to shorten the title", weights=1),
            ]
        )
        content_structure.add_section(title_blocks)

        self._add_sections(content_structure, style, template_id, params)

        if nearby_places and len(nearby_places) > 0:
            nearby_values = [
                f"{k}: {', '.join(np.random.permutation(v).tolist())}"
                for k, v in nearby_places.items()
                if v
            ]
            nearby_input = "; ".join(nearby_values)
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.4. Nearby Places: nearby amenities and important places.",
                    contents=[
                        random_use(
                            "- Only mention some nearby places, not all", weights=0.5
                        ),
                        random_use_one_in_list(
                            [
                                "- Heading 'Địa điểm xung quanh' in Vietnamese",
                                "- Heading 'Tiện ích xung quanh' in Vietnamese",
                            ]
                        ),
                    ],
                )
            )
        else:
            nearby_input = ""

        if project:
            project_values = [
                f"{k}: {v}"
                for k, v in project.model_dump().items()
                if v not in [None, ""] and k not in ["project_id", "summary", "legal"]
            ]
            project_input = "; ".join(project_values)
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.5. Project: extra information about the project.",
                    contents=[
                        "- DO NOT mention the legality from the project information",
                        "- DO NOT mix the project information with other sections",
                        random_use_one_in_list(
                            [
                                "- Heading 'Thông tin dự án' in Vietnamese",
                                "- Heading 'Giới thiệu dự án' in Vietnamese",
                            ]
                        ),
                    ],
                )
            )
        else:
            project_input = ""

        content_structure.add_section(
            PromptSectionTemplate(
                name="3. Ending: Include a call to action (CTA) in the conclusion.",
                contents=[
                    "Write the CTA using the phone tag <contact_phone> and the name "
                    "tag <contact_name>.",
                    "Indicate the contact person's name and phone number.",
                    "DO NOT mention 'sở hữu' or 'mua ngay' in for sale case.",
                ],
            )
        )
        prompt_template.add_section(content_structure)

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

        prompt_template.add_section(
            PromptSectionTemplate(name="#Input", contents=[_params_str])
        )
        prompt_template.add_section(rule_blocks)
        prompt_template.add_variables(params_dict)

        structured = self._chat_model.with_structured_output(Content, include_raw=True)
        content_out: Content | None = None
        raw = None
        title_ok = False
        for attempt in range(_MAX_TITLE_ATTEMPTS):
            result = await structured.ainvoke(
                prompt_template.to_api_message(), config=self._trace_config
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
            "prompt": prompt_template.to_str(),
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

    def _add_sections(
        self,
        content_structure: PromptSectionTemplate,
        style: StyleType,
        template_id: ProfessionalTemplateType | SimpleTemplateType,
        params: PairAddressParams,
    ) -> None:
        is_rent = params.goal == GoalTypeVN.RENT
        is_sale = params.goal == GoalTypeVN.SALE
        has_furniture = bool(
            params.interior
            and params.interior.lower() in [InteriorTypeVN.FULL, InteriorTypeVN.BASIC]
        )
        legality = (params.legality or "").lower()
        red_book_sale = legality in [LegalityTypeVN.RED_BOOK] and is_sale
        waiting_sale = legality in [LegalityTypeVN.WAITING] and is_sale

        # Opening — note the {ADDRESS_PLACEHOLDER} instruction (pair-address specific).
        opening = [
            "- DO NOT start with 'Chào mừng, chào đón' or similar phrases",
            "- DO NOT mention target users",
            "- Use '{ADDRESS_PLACEHOLDER}' as placeholder for property address",
            "- DO NOT use actual address, only the placeholder {ADDRESS_PLACEHOLDER}",
        ]
        if style == StyleType.PROFESSIONAL:
            opening.append(
                random_use(
                    f"- Start with {np.random.choice(['Nhanh tay'])}", weights=0.2
                )
            )
        content_structure.add_section(
            PromptSectionTemplate(
                name="2.1. Opening: overview + key attributes.", contents=opening
            )
        )

        if style == StyleType.PROFESSIONAL:
            if template_id not in set(ProfessionalTemplateType):
                raise ValueError(f"Template {template_id} not supported for {style}")
            body = PromptSectionTemplate(
                name="2.2. Highlight selling points and standout features.",
                contents=[
                    "- Mention the property's price, and key attributes.",
                    "- DO NOT mention nearby places in this section",
                    random_use(
                        "- List some furniture items (e.g. 'điều hòa, tủ lạnh').",
                        condition=has_furniture,
                    ),
                    random_use(
                        "- Highlight flexible rental time if the goal is for rent.",
                        condition=is_rent,
                    ),
                    random_use("- Highlight 'phong thủy' if any", condition=is_sale),
                    "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                    "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                    "- Highlight 'mặt tiền' if suitable for business"
                    if params.width
                    else "",
                ],
            )
            content_structure.add_section(body)
        elif style == StyleType.SIMPLE:
            if template_id != SimpleTemplateType.TEMPLATE1:
                raise ValueError(f"Template {template_id} not supported for {style}")
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.2. Highlight selling points and standout features.",
                    contents=[
                        "- Mention the property's price, and key attributes.",
                        "- No heading in this part",
                        "- DO NOT mention nearby places or utilities in this section",
                        random_use(
                            "- If nội thất is 'đầy đủ', list some furniture items.",
                            condition=has_furniture,
                        ),
                        random_use(
                            "- Highlight flexible rental time if the goal is for rent.",
                            condition=is_rent,
                        ),
                        random_use(
                            "- Highlight 'phong thủy' if any", condition=is_sale
                        ),
                    ],
                )
            )
        else:
            raise ValueError("Style not supported")
