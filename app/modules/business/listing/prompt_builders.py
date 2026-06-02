"""Shared prompt-section builders for the listing generators.

Both the description and pair-address generators compose the same prompt
sections (#Role / #Tone / #Rules / Title / description-template / Nearby /
Project / Ending) via these builders. The small per-generator differences are
parameters:

- ``address_options`` — the title's address-usage examples (static for
  description, address-derived for pair-address).
- ``address_placeholder`` — whether the opening tells the LLM to emit the
  ``{ADDRESS_PLACEHOLDER}`` token (pair-address only).

Centralizing here removes ~250 lines of duplication per generator and gives a
single place to evolve prompt content (e.g. restore full legacy wording).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.core.config import Settings
from app.modules.business.listing.config import (
    GoalTypeVN,
    InteriorTypeVN,
    LegalityTypeVN,
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
from app.modules.business.listing.utils import (
    cvt_shorten_number,
    number_standardize,
    random_use,
    random_use_one_in_list,
)

DESCRIPTION_ADDRESS_OPTIONS = [
    '- USE district and city in the title. e.g: "Q7, HCM"',
    '- USE ward, district, and city in the title. e.g: "Tân Phong, Quận 7, HCM"',
    '- USE full address in the title. e.g: "Nguyễn Văn Linh, Tân Phong, Quận 7, TP.HCM"',
]


def apply_price_area_formatting(params_dict: dict[str, Any]) -> None:
    """Mutate ``params_dict`` with formatted price/area + ``is_price_available``."""
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


def add_role_and_tone(
    prompt: OpenAIPromptTemplate, params: Any, tone: ToneType
) -> None:
    prompt.add_section(
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
        prompt.add_section(
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
        prompt.add_section(
            PromptSectionTemplate(
                name="#Tone",
                contents=[
                    "Target users are all customers, aged 30-50",
                    "Write in a professional tone to attract potential buyers "
                    "or renters.",
                ],
            )
        )


def build_rules(params: Any, params_dict: dict[str, Any]) -> PromptSectionTemplate:
    return PromptSectionTemplate(
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
                '- Use dashes "-" for headings and "+" for bullet points.', weights=0.6
            ),
            "- DO NOT highlight the benefits of price, just mention 'giá thỏa thuận'"
            if params.price_unit == PriceVNUnitType.NEGOTIABLE
            else "",
        ],
    )


def pick_hook_str(
    params_dict: dict[str, Any], style: StyleType, max_hook_words: int
) -> str:
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
    return "\n".join(np.random.choice(hooks, max_hook_words))


def build_title_section(
    params: Any, hook_str: str, address_options: list[str]
) -> PromptSectionTemplate:
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
            random_use(random_use_one_in_list(address_options), weights=0.8),
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
    return title_blocks


def add_description_sections(
    content_structure: PromptSectionTemplate,
    style: StyleType,
    template_id: ProfessionalTemplateType | SimpleTemplateType,
    params: Any,
    *,
    address_placeholder: bool = False,
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

    opening = [
        "- DO NOT start with 'Chào mừng, chào đón' or similar phrases",
        "- DO NOT mention target users",
    ]
    if address_placeholder:
        opening += [
            "- Use '{ADDRESS_PLACEHOLDER}' as placeholder for property address",
            "- DO NOT use actual address, only the placeholder {ADDRESS_PLACEHOLDER}",
        ]
    if style == StyleType.PROFESSIONAL:
        opening.append(
            random_use(f"- Start with {np.random.choice(['Nhanh tay'])}", weights=0.2)
        )
    content_structure.add_section(
        PromptSectionTemplate(
            name="2.1. Opening: overview + key attributes.", contents=opening
        )
    )

    if style == StyleType.PROFESSIONAL:
        if template_id == ProfessionalTemplateType.TEMPLATE1:
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.2. Topic 1: essential features and their benefits.",
                    contents=[
                        f"- Use {random_use('-', '+')} to separate the item points.",
                        "- Use \n at the end of each item.",
                        "- Mention the property's price, and key attributes.",
                        random_use(
                            "- List some furniture items (e.g. 'điều hòa, tủ lạnh').",
                            condition=has_furniture,
                        ),
                        random_use(
                            "- Highlight flexible rental time if the goal is for rent.",
                            condition=is_rent,
                        ),
                        random_use(
                            "- Use full words for 'phòng ngủ', 'phòng tắm', etc.",
                            weights=0.5,
                        ),
                    ],
                )
            )
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.3. Topic 2: unique selling points / standout features.",
                    contents=[
                        "- DO NOT mention nearby places in this section",
                        random_use(
                            "- Hightlight 'phong thủy' if any", condition=is_sale
                        ),
                        random_use(
                            "- Highlight lifestyle, convenience, or nearby places",
                            condition=is_sale,
                        ),
                        "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                        "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                        "- Highlight 'mặt tiền' if suitable for business"
                        if params.width
                        else "",
                    ],
                )
            )
        elif template_id in (
            ProfessionalTemplateType.TEMPLATE2,
            ProfessionalTemplateType.TEMPLATE3,
        ):
            content_structure.add_section(
                PromptSectionTemplate(
                    name="2.2. Unique selling points / standout features.",
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
                            "- List some furniture items (e.g. 'điều hòa, tủ lạnh').",
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
                        "- Highlight 'pháp lý đầy đủ'" if red_book_sale else "",
                        "- Inform 'pháp lý' in waiting status" if waiting_sale else "",
                        random_use(
                            "- Highlight flexible rental time if the goal is for rent.",
                            condition=is_rent,
                        ),
                    ],
                )
            )
        else:
            raise ValueError(f"Template {template_id} not supported for {style}")
    elif style == StyleType.SIMPLE:
        if template_id != SimpleTemplateType.TEMPLATE1:
            raise ValueError(f"Template {template_id} not supported for {style}")
        content_structure.add_section(
            PromptSectionTemplate(
                name="2.2. Unique selling points / standout features.",
                contents=[
                    "- Mention the property's price, and key attributes.",
                    "- No heading in this part",
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
                        "- Highlight flexible rental time if the goal is for rent.",
                        condition=is_rent,
                    ),
                    random_use("- Hightlight 'phong thủy' if any", condition=is_sale),
                ],
            )
        )
    else:
        raise ValueError("Style not supported")


def build_nearby_section(
    nearby_places: dict[str, list[str]], settings: Settings
) -> tuple[PromptSectionTemplate | None, str]:
    if not nearby_places:
        return None, ""
    nearby_values = [
        f"{k}: {', '.join(np.random.permutation(v).tolist())}"
        for k, v in nearby_places.items()
        if v
    ]
    nearby_input = "; ".join(nearby_values)
    section = PromptSectionTemplate(
        name="2.4. Nearby Places: nearby amenities and important places.",
        contents=[
            random_use("- Only mention some nearby places, not all", weights=0.5),
            random_use_one_in_list(
                [
                    random_use_one_in_list(
                        [
                            "- Heading 'Địa điểm xung quanh' in Vietnamese",
                            "- Heading 'Khu vực xung quanh' in Vietnamese",
                            "- Heading 'Tiện ích xung quanh' in Vietnamese",
                        ]
                    ),
                    random_use_one_in_list(
                        [
                            '- List nearby amenities such as "gần trường học", '
                            '"gần chợ/siêu thị", "có công viên,"',
                            "- List nearby amenities such as 'cách trường học', "
                            "'cách chợ/siêu thị', 'cách công viên' tầm "
                            f"{settings.GMAP_PG_RADIUS}m (use km insteads)",
                            "- Highlight the convenience of nearby amenities",
                        ]
                    ),
                ]
            ),
        ],
    )
    return section, nearby_input


def build_project_section(project: Any) -> tuple[PromptSectionTemplate | None, str]:
    if not project:
        return None, ""
    project_values = [
        f"{k}: {v}"
        for k, v in project.model_dump().items()
        if v not in [None, ""] and k not in ["project_id", "summary", "legal"]
    ]
    project_input = "; ".join(project_values)
    section = PromptSectionTemplate(
        name="2.5. Project: extra information about the project.",
        contents=[
            "- DO NOT mention the legality from the project information",
            "- DO NOT mix the project information with other sections",
            random_use("- Use \n at the end of each item.", weights=0.6),
            random_use_one_in_list(
                [
                    "- Heading 'Thông tin dự án' in Vietnamese",
                    "- Heading 'Chi tiết dự án' in Vietnamese",
                    "- Heading 'Giới thiệu dự án' in Vietnamese",
                ]
            ),
            random_use_one_in_list(
                [
                    "- Rewrite the project's location, investor, utility, and design",
                    "- Highlight the project's location, investor, utility, and design",
                    "- Rewrite the project information in a paragraph",
                ]
            ),
        ],
    )
    return section, project_input


def build_ending_section() -> PromptSectionTemplate:
    return PromptSectionTemplate(
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
