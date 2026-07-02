"""Enums + small value types for the listing generator.

Ported behavior-frozen from bds-genai-dgl ``core/generator/config.py`` and
``core/submit/config.py`` — values match legacy exactly. Prompt-text constants
and ``ParamLangMap`` are deferred to the Phase 2 generator port.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import ClassVar

from pydantic import BaseModel

# Legacy datetime format (settings.DATETIME_FORMAT) — used for reset_date
# strings and JSON-serialized listing timestamps.
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class PropertyType(StrEnum):
    HOUSE = "house"
    DEPARTMENT = "department"
    LAND_LOT = "land lot"


class GoalType(StrEnum):
    RENT = "rent"
    SALE = "sale"


class GoalTypeVN(StrEnum):
    RENT = "cho thuê"
    SALE = "bán"


class LegalityTypeVN(StrEnum):
    RED_BOOK = "sổ đỏ/ sổ hồng"
    SALE_CONTRACT = "hợp đồng mua bán"
    WAITING = "đang chờ sổ"


class InteriorTypeVN(StrEnum):
    FULL = "đầy đủ"
    BASIC = "cơ bản"
    NONE = "không nội thất"


class LanguageType(StrEnum):
    VI = "Vietnamese"
    EN = "English"


class DirectionType(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"


class PriceUnitType(StrEnum):
    CURRENCY_VND = "VND"
    UNIT_M2 = "Price / m²"
    NEGOTIABLE = "Negotiable"


class PriceVNUnitType(StrEnum):
    CURRENCY_VND = "VND"
    UNIT_M2 = "Giá / m²"
    NEGOTIABLE = "Thoả thuận"


class AreaUnitType(StrEnum):
    M2 = "m2"


class AddressVersionType(IntEnum):
    OLD = 0
    NEW = 1


class StyleType(StrEnum):
    SIMPLE = "simple"
    PROFESSIONAL = "professional"


class ToneType(StrEnum):
    SIMPLE = "simple"
    PROFESSIONAL = "professional"


class AuthorType(StrEnum):
    AI = "ai"
    USER = "user"


class PlatformType(StrEnum):
    WEB = "web"
    MOBILE = "mobile"
    MOBILE_WEB = "mobile_web"
    EMPTY = ""


class ProfessionalTemplateType(StrEnum):
    TEMPLATE1 = "professional_template_1"
    TEMPLATE2 = "professional_template_2"
    TEMPLATE3 = "professional_template_3"


class SimpleTemplateType(StrEnum):
    TEMPLATE1 = "simple_template_1"


class TemplateResponse(BaseModel):
    selected_template: ProfessionalTemplateType | SimpleTemplateType


class ParamLangMap:
    """Maps param keys/values to Vietnamese for the prompt input (verbatim)."""

    items: ClassVar[dict[str, dict[str, str]]] = {
        "goal": {"vi": "mục tiêu", "en": "goal"},
        "property_type": {"vi": "loại bất động sản", "en": "property type"},
        "area": {"vi": "diện tích", "en": "area"},
        "price": {"vi": "giá", "en": "price"},
        "price_unit": {"vi": "đơn vị giá", "en": "price unit"},
        "legality": {"vi": "pháp lý", "en": "legality"},
        "project": {"vi": "dự án", "en": "project"},
        "city": {"vi": "thành phố", "en": "city"},
        "district": {"vi": "quận", "en": "district"},
        "ward": {"vi": "phường", "en": "ward"},
        "street": {"vi": "đường", "en": "street"},
        "address": {"vi": "địa chỉ", "en": "address"},
        "display_address": {"vi": "địa chỉ đầy đủ", "en": "display address"},
        "new_city": {"vi": "thành phố mới", "en": "new city"},
        "new_ward": {"vi": "phường mới", "en": "new ward"},
        "new_street": {"vi": "đường mới", "en": "new street"},
        "new_display_address": {
            "vi": "địa chỉ đầy đủ mới",
            "en": "new display address",
        },
        "contact_name": {"vi": "tên người liên hệ", "en": "contact name"},
        "contact_phone": {"vi": "số điện thoại liên hệ", "en": "contact phone"},
        "contact_email": {"vi": "email liên hệ", "en": "contact email"},
        "style": {"vi": "phong cách viết", "en": "style"},
        "tone": {"vi": "tông giọng", "en": "tone"},
        "interior": {"vi": "nội thất", "en": "interior"},
        "rooms": {"vi": "số phòng ngủ", "en": "rooms"},
        "toilets": {"vi": "số toilet", "en": "toilets"},
        "floors": {"vi": "số lượng tầng", "en": "floors"},
        "direction": {"vi": "hướng cửa chính", "en": "direction"},
        "balcon_direction": {"vi": "hướng ban công", "en": "balcon direction"},
        "width": {"vi": "chiều ngang mặt tiền", "en": "width"},
        "road_width": {"vi": "chiều rộng ngõ trước", "en": "road width"},
        "creative": {"vi": "sáng tạo", "en": "creative"},
        "simple": {"vi": "đơn giản", "en": "simple"},
        "professional": {"vi": "chuyên nghiệp", "en": "professional"},
        "formatted_price": {"vi": "giá", "en": "price"},
        "formatted_area": {"vi": "diện tích", "en": "area"},
        "formatted_address": {"vi": "địa chỉ", "en": "address"},
    }

    @classmethod
    def get(cls, key: object, lang: str = "vi") -> object:
        lookup_key = str(key)
        return cls.items.get(lookup_key, {}).get(lang, key)
