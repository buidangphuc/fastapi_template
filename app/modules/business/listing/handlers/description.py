"""Description generator (ported from bds-genai-dgl
core/generator/service/description.py).

The prompt-building is kept **verbatim** (behavior-frozen). The only swap: the
legacy ``client.beta.chat.completions.parse(..., response_format=Content)`` call
becomes langchain ``chat_model.with_structured_output(Content, include_raw=True)``
— same structured schema — and token usage is mapped from the raw message's
``usage_metadata`` back to the legacy ``tokens.usage.*`` shape. Nearby/project
services and the chat model are injected (no import-time singletons).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field

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
from app.modules.business.listing.prompt import (
    OpenAIPromptTemplate,
    PromptSectionTemplate,
)
from app.modules.business.listing.schemas import AllParams
from app.modules.business.listing.utils import (
    cvt_shorten_number,
    number_standardize,
    random_use,
    random_use_one_in_list,
)


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
            # Location mapping was dropped; NEW addresses rely on lat/lng only.
            place = None
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
        return nearby_places

    async def get_project(self, params: AllParams) -> Any:
        return await self._project.get_summary(project_id=params.project_id)

    async def _gather_context(
        self,
        params: AllParams,
        address_version: AddressVersionType,
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

        # --- Preprocess params -------------------------------------------------
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

        # --- Build prompt ------------------------------------------------------
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

        # Title
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
            logger.debug("> Add price hooks")

        if style == StyleType.PROFESSIONAL:
            pass
        elif style == StyleType.SIMPLE:
            hooks.extend(["hàng hot", "bao đẹp", "đẹp xuất sắc", "siêu hot"])
        else:
            raise ValueError("Style not supported")
        hook = np.random.choice(hooks, self._settings.MAX_HOOK_WORDS)
        hook_str = "\n".join(hook)

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
        title_blocks.add_contents(
            [
                random_use(
                    random_use_one_in_list(
                        [
                            '- USE district and city in the title. e.g: "Q7, HCM"',
                            "- USE ward, district, and city in the title. e.g: "
                            '"Tân Phong, Quận 7, HCM"',
                            '- USE full address in the title. e.g: "Nguyễn Văn Linh, '
                            'Tân Phong, Quận 7, TP.HCM"',
                        ]
                    ),
                    weights=0.8,
                ),
                random_use(
                    "- Write with engaging title to capture attention from potential "
                    f"buyers or renters, combining with the following hooks: {hook_str}",
                    weights=0.8,
                ),
                random_use(
                    """
- Use abbreviations for address if possible.
    - "đường Nguyễn Văn Linh, Phường Tân Phong, Quận 7, TP.HCM" -> "Nguyễn Văn Linh, Tân Phong, Quận 7, TP.HCM"
    - "đường Nguyễn Văn Linh, Phường Tân Phong, Quận 7, TP.HCM" -> "Nguyễn Văn Linh, p Tân Phong, Q7, TP.HCM"
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
                random_use(
                    """
- Use abbreviations for property types, such as:
  - chung cư: CC
  - nhà riêng: NR
  - biệt thự: BT
  - nhà phố: NP
  - căn hộ: CH
  - đất nền: DN
  - đất thổ cư: DTC
""",
                    weights=1,
                ),
                random_use(f"- MUST include goal in Title: {params.goal}", weights=1),
                random_use("- Can use abbreviations to shorten the title", weights=1),
            ]
        )
        content_structure.add_section(title_blocks)

        # Description (style/template specific) — full verbatim port.
        self._add_description_sections(content_structure, style, template_id, params)

        # Nearby places
        if len(nearby_places) > 0:
            nearby_values = [
                f"{k}: {', '.join(np.random.shuffle(v) or v)}"
                for k, v in nearby_places.items()
                if v
            ]
            nearby_input = "; ".join(nearby_values)
            nearby_places_block = PromptSectionTemplate(
                name="2.4. Nearby Places: Provide information about nearby amenities "
                "and important places.",
                contents=[
                    random_use(
                        "- Only mention some nearby places, not all", weights=0.5
                    ),
                    random_use_one_in_list(
                        [
                            random_use_one_in_list(
                                [
                                    "- Separate nearby as a new block with heading "
                                    "'Địa điểm xung quanh' in Vietnamese",
                                    "- Separate nearby as a new block with heading "
                                    "'Khu vực xung quanh' in Vietnamese",
                                    "- Separate nearby as a new block with heading "
                                    "'Tiện ích xung quanh' in Vietnamese",
                                    "- Separate nearby as a new block with heading "
                                    "'Địa điểm tiện ích xung quanh' in Vietnamese",
                                ]
                            ),
                            random_use_one_in_list(
                                [
                                    '- List nearby amenities such as "gần trường học", '
                                    '"gần chợ/siêu thị", "có công viên,"',
                                    "- List nearby amenities such as 'cách trường học', "
                                    "'cách chợ/siêu thị', 'cách công viên' tầm "
                                    f"{self._settings.GMAP_PG_RADIUS}m (use km insteads)",
                                    "- Highlight the convenience of nearby amenities "
                                    "without advertising these places",
                                ]
                            ),
                        ]
                    ),
                ],
            )
            content_structure.add_section(nearby_places_block)
        else:
            nearby_input = ""

        if project:
            project_values = [
                f"{k}: {v}"
                for k, v in project.model_dump().items()
                if v not in [None, ""] and k not in ["project_id", "summary", "legal"]
            ]
            project_input = "; ".join(project_values)
            project_block = PromptSectionTemplate(
                name="2.5. Project: Provide extra information about the project.",
                contents=[
                    "- DO NOT mention the legality from the project information",
                    "- DO NOT mix the project information with other sections",
                    random_use("- Use \n at the end of each item.", weights=0.6),
                    random_use_one_in_list(
                        [
                            "- Separate nearby as a new block with heading "
                            "'Thông tin dự án' in Vietnamese",
                            "- Separate nearby as a new block with heading "
                            "'Thông tin thêm về dự án' in Vietnamese",
                            "- Separate nearby as a new block with heading "
                            "'Chi tiết dự án' in Vietnamese",
                            "- Separate nearby as a new block with heading "
                            "'Giới thiệu tổng quan dự án' in Vietnamese",
                            "- Separate nearby as a new block with heading "
                            "'Giới thiệu dự án' in Vietnamese",
                        ]
                    ),
                    random_use_one_in_list(
                        [
                            "- Rewrite the project's location, investor, utility, "
                            "and design",
                            "- Highlight the project's location, investor, utility, "
                            "and design separately",
                            "- Rewrite the project information in a paragraph and "
                            "highlight the project advantages",
                        ]
                    ),
                ],
            )
            content_structure.add_section(project_block)
        else:
            project_input = ""

        description_ending_blocks = PromptSectionTemplate(
            name="3. Ending: Include a call to action (CTA) in the conclusion.",
            contents=[
                "Write the CTA using the phone tag <contact_phone> and the name "
                "tag <contact_name>.",
                "Indicate the contact person's name and phone number.",
                "DO NOT mention 'sở hữu' or 'mua ngay' in for sale case.",
                random_use(
                    random_use_one_in_list(
                        [
                            "Highlight the free consultation.",
                            "Just tell please contact for more information",
                            "Contact for more details",
                        ]
                    ),
                    weights=0.7,
                ),
            ],
        )
        content_structure.add_section(description_ending_blocks)
        prompt_template.add_section(content_structure)

        # --- Input + ignored params -------------------------------------------
        _params_ignore = []
        for key, value in params_dict.copy().items():
            if not value or (isinstance(value, int | float) and value <= 0):
                params_dict.pop(key)
                _params_ignore.append(key)
        _params_ignore.extend(["lat", "lng", "is_price_available"])

        ignore_str = ", ".join([str(ParamLangMap.get(key)) for key in _params_ignore])
        rule_blocks.add_content(f"DO NOT include {ignore_str} in the content.")

        _params_str = ",".join(
            f"{ParamLangMap.get(key)}:{value}" for key, value in params_dict.items()
        )
        if self._settings.GMAP_PG_ENABLE and len(nearby_places) > 0:
            _params_str = _params_str + "," + nearby_input
        if self._settings.PROJECT_ENABLE and project:
            _params_str = _params_str + "," + project_input

        prompt_template.add_section(
            PromptSectionTemplate(name="#Input", contents=[_params_str])
        )
        prompt_template.add_section(rule_blocks)
        prompt_template.add_variables(params_dict)

        # --- LLM call (structured output via ai/llm) --------------------------
        structured = self._chat_model.with_structured_output(Content, include_raw=True)
        result = await structured.ainvoke(
            prompt_template.to_api_message(), config=self._trace_config
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
            "prompt": prompt_template.to_str(),
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

    def _add_description_sections(
        self,
        content_structure: PromptSectionTemplate,
        style: StyleType,
        template_id: ProfessionalTemplateType | SimpleTemplateType,
        params: AllParams,
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

        if style == StyleType.PROFESSIONAL:
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.1. Opening: Provide an overview that highlights the "
                    "property's location, type, and key attributes.",
                    contents=[
                        "- Do not start with 'Chào mừng, chào đón' or similar phrases",
                        random_use(
                            f"- Start with {np.random.choice(['Nhanh tay'])}",
                            weights=0.2,
                        ),
                    ],
                )
            )

            if template_id == ProfessionalTemplateType.TEMPLATE1:
                block1 = PromptSectionTemplate(
                    name="2.2. Topic 1: List essential features and emphasize their "
                    "benefits.",
                    contents=[
                        f"- Use {random_use('-', '+')} to separate the item points.",
                        "- Use \n at the end of each item.",
                        "- Mention the property's price, and key attributes.",
                        random_use(
                            "- List some furniture items. For example, 'điều hòa, "
                            "giường, tủ lạnh...' or 'điều hòa, tủ lạnh,...'",
                            condition=has_furniture,
                        ),
                        random_use(
                            "- Highlight the flexible rental time, at least "
                            f"{np.random.choice(['1 year', '6 months'])} if for rent.",
                            condition=is_rent,
                        ),
                        random_use(
                            "- Use full words for 'phòng ngủ', 'phòng tắm', etc.",
                            weights=0.5,
                        ),
                    ],
                )
                block2 = PromptSectionTemplate(
                    name="2.3. Topic 2: Mention unique selling points or standout "
                    "features that add value.",
                    contents=[
                        "- DO NOT mention nearby places in this section",
                        random_use(
                            "- Topic name can be "
                            f"{np.random.choice(['Điểm đặc biệt', 'Điểm nổi bật', 'Ưu điểm', 'Điểm nhấn', 'Điểm cộng'])}"
                        ),
                        random_use(
                            "- Hightlight 'phong thủy' if any", condition=is_sale
                        ),
                        random_use(
                            "- Highlight lifestyle, convenience, or nearby places",
                            condition=is_sale,
                        ),
                        "- Highlight 'ngõ vào or đường vào' whether suitable for car"
                        if params.road_width
                        else "",
                        "- Highlight 'mặt tiền' whether suitable for business"
                        if params.width
                        else "",
                        "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                        "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                    ],
                )
                content_structure.add_section(block1)
                content_structure.add_section(block2)
            elif template_id in (
                ProfessionalTemplateType.TEMPLATE2,
                ProfessionalTemplateType.TEMPLATE3,
            ):
                block = PromptSectionTemplate(
                    name="2.2. Mention unique selling points or standout features "
                    "that add value for potential buyers or renters.",
                    contents=[
                        "- Mention the property's price, and key attributes.",
                        "- DO NOT mention nearby places in this section",
                        "- Each point should be a single line.",
                        random_use(
                            "- Combine 'phòng ngủ' and 'phòng tắm' in the same sentence.",
                            condition=bool(params.rooms and params.toilets),
                            weights=0.6,
                        ),
                        random_use(
                            "- List some furniture items. For example, 'điều hòa, "
                            "giường, tủ lạnh...'",
                            condition=has_furniture,
                            weights=0.7,
                        ),
                        random_use(
                            "- Hightlight 'phong thủy' if any", condition=is_sale
                        ),
                        random_use(
                            "- Highlight lifestyle, convenience, or nearby places",
                            condition=is_sale,
                        ),
                        "- Highlight 'ngõ vào or đường vào' whether suitable for car"
                        if params.road_width
                        else "",
                        "- Highlight 'mặt tiền' whether suitable for business"
                        if number_standardize(params.width)
                        else "",
                        "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                        "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                        random_use(
                            "- Highlight the flexible rental time, at least "
                            f"{np.random.choice(['1 year', '6 months'])} if for rent.",
                            condition=is_rent,
                        ),
                    ],
                )
                content_structure.add_section(block)
            else:
                raise ValueError(f"Template {template_id} not supported for {style}")

        elif style == StyleType.SIMPLE:
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.1. Opening: Provide an overview that highlights the "
                    "property's location, type, and key attributes and list "
                    "essential features.",
                    contents=[
                        "- DO NOT start with 'Chào mừng, chào đón' or similar phrases"
                        "- DO NOT mention target users"
                    ],
                )
            )
            if template_id == SimpleTemplateType.TEMPLATE1:
                block = PromptSectionTemplate(
                    name="2.2. Topic: Mention unique selling points or standout "
                    "features that add value for potential buyers or renters.",
                    contents=[
                        "- Mention the property's price, and key attributes.",
                        "- No heading in this part",
                        "- Layout-free layout",
                        "- DO NOT mention nearby places or utilities in this section",
                        random_use(
                            random_use_one_in_list(
                                [
                                    "- Each sentence MUST END with '\n\n'",
                                    "- Separate the benefit points with a new line",
                                ]
                            ),
                            weights=0.4,
                        ),
                        random_use(
                            "- If nội thất is 'đầy đủ', list some furniture items.",
                            condition=has_furniture,
                        ),
                        random_use(
                            "- Highlight the flexible rental time, at least "
                            f"{np.random.choice(['1 year', '6 months'])} if for rent.",
                            condition=is_rent,
                        ),
                        random_use(
                            "- Hightlight life style, convenience, or nearby places"
                        ),
                        random_use(
                            "- Hightlight 'phong thủy' if any", condition=is_sale
                        ),
                        "- Highlight 'mặt tiền' whether suitable for business"
                        if params.width
                        else "",
                        "- Highlight 'ngõ or đường vào' whether suitable for car"
                        if params.road_width
                        else "",
                        "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                        "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                    ],
                )
                content_structure.add_section(block)
            else:
                raise ValueError(f"Template {template_id} not supported for {style}")
        else:
            raise ValueError("Style not supported")
