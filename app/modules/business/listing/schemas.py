"""Request/response schemas for the listing generator.

Ported behavior-frozen from bds-genai-dgl ``core/generator/schema`` and
``core/limiter/schema``.

NOTE (Phase 2 follow-up): legacy ``contact_email`` is a pydantic ``EmailStr``
(email-format validation). It is kept as ``str`` here to avoid adding the
``email-validator`` dependency in the scaffold; restore ``EmailStr`` when the
endpoint is wired. Tracked in docs/migration/phase-log.md.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.business.listing.config import (
    AreaUnitType,
    GoalTypeVN,
    PlatformType,
    PriceVNUnitType,
    StyleType,
)


class SchemaBase(BaseModel):
    # Matches legacy common.schema.SchemaBase (serialize enums by value).
    model_config = ConfigDict(use_enum_values=True)


class RemainResponse(BaseModel):
    used_requests: int = Field(..., description="Used requests")
    total_requests: int = Field(..., description="Total requests")
    reset_date: str = Field(..., description="Reset date. Format: %Y-%m-%d %H:%M:%S")


class ChangeDayLimit(BaseModel):
    limit: int = Field(..., description="Day limit for all users")


class SubmitListing(BaseModel):
    user_id: str = Field(..., description="User ID")
    listing_id: str = Field(..., description="Listing ID")
    title: str = Field(..., description="Title")
    description: str = Field(..., description="Description")
    style: StyleType = Field(..., description="Style: simple or professional")
    platform: PlatformType = Field(description="Platform", default=PlatformType.EMPTY)


class Params(SchemaBase):
    goal: GoalTypeVN = Field(description="Goal")
    property_type: str = Field(description="Property type")
    area: float = Field(description="Area")
    area_unit: AreaUnitType | None = Field(description="Area", default=AreaUnitType.M2)
    price: float = Field(description="Price")
    price_unit: PriceVNUnitType = Field(description="Price unit")
    legality: str | None = Field(
        description="Legality. For example: red book, pink book, etc.", default=None
    )
    project: str | None = Field(description="Real Estate Project", default=None)

    # Address information
    city: str = Field(description="City")
    district: str = Field(description="District")
    ward: str = Field(description="Ward")
    street: str | None = Field(description="Street", default=None)
    display_address: str | None = Field(
        description="User-editted address", default=None
    )

    # Contact information
    contact_name: str = Field(description="Contact name")
    contact_phone: str = Field(description="Contact phone")
    contact_email: str | None = Field(description="Contact email", default=None)
    lat: float | None = Field(description="Latitude", default=None)
    lng: float | None = Field(description="Longitude", default=None)

    @field_validator("city")
    @classmethod
    def check_city(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("city is required")
        return value

    @field_validator("district")
    @classmethod
    def check_district(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("district is required")
        return value

    @field_validator("ward")
    @classmethod
    def check_ward(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("ward is required")
        return value

    @field_validator("contact_name")
    @classmethod
    def check_contact_name(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("contact_name is required")
        return value

    @field_validator("contact_phone")
    @classmethod
    def check_contact_phone(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("contact_phone is required")
        return value

    @field_validator("area_unit")
    @classmethod
    def check_area_unit(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("area_unit is required")
        return value

    @model_validator(mode="after")
    def check_price(self) -> Params:
        priced_units = (PriceVNUnitType.CURRENCY_VND, PriceVNUnitType.UNIT_M2)
        if self.price_unit in priced_units and self.price <= 0:
            raise ValueError(
                "price must be greater than or equal to 0 because "
                f"price_unit is {self.price_unit}"
            )
        if self.price_unit == PriceVNUnitType.NEGOTIABLE and self.price > 0:
            raise ValueError("price must be 0")
        return self


class AllParams(Params):
    interior: str | None = Field(description="Interior", default=None)
    rooms: int | None = Field(description="Number of rooms", default=None)
    toilets: int | None = Field(description="Number of toilets", default=None)
    floors: int | None = Field(description="Number of floors", default=None)
    direction: str | None = Field(
        description="Direction of the main door", default=None
    )
    balcon_direction: str | None = Field(
        description="Direction of the balcony", default=None
    )
    width: float | None = Field(description="Width", default=None)
    road_width: float | None = Field(
        description="Width of the front road", default=None
    )

    project_id: str | None = Field(description="Project ID", default=None)
    platform: PlatformType | None = Field(
        description="Platform", default=PlatformType.EMPTY
    )

    # Backward-compatible mapping fields. NOTE: location mapping itself is
    # dropped (see ADR) — these remain as inert, optional inputs for contract
    # compatibility.
    city_code: str | None = Field(
        description="City code (legacy, optional)", default=None
    )
    district_id: int | None = Field(
        description="District ID (legacy, optional)", default=None
    )
    ward_id: int | None = Field(description="Ward ID (legacy, optional)", default=None)
    street_id: int | None = Field(
        description="Street ID (legacy, optional)", default=None
    )

    @field_validator("width")
    @classmethod
    def check_width(cls, value: Any) -> Any:
        if value is not None and float(value) < 0:
            raise ValueError("width must be greater than 0")
        return value

    @field_validator("road_width")
    @classmethod
    def check_road_width(cls, value: Any) -> Any:
        if value is not None and float(value) < 0:
            raise ValueError("road_width must be greater than 0")
        return value

    @field_validator("rooms")
    @classmethod
    def check_rooms(cls, value: Any) -> Any:
        if value is not None and value < 0:
            raise ValueError("rooms must be greater than or equal to 0")
        return value

    @field_validator("toilets")
    @classmethod
    def check_toilets(cls, value: Any) -> Any:
        if value is not None and value < 0:
            raise ValueError("toilets must be greater than or equal to 0")
        return value

    @field_validator("floors")
    @classmethod
    def check_floors(cls, value: Any) -> Any:
        if value is not None and value < 0:
            raise ValueError("floors must be greater than or equal to 0")
        return value


class PairAddressParams(AllParams):
    new_city: str = Field(
        description="City where the property is located (new address)"
    )
    new_ward: str = Field(description="Ward or subdistrict (new address)")
    new_street: str | None = Field(
        description="Street address of the property (new address)", default=None
    )
    new_display_address: str | None = Field(
        description="Full address to be displayed (new address)", default=None
    )

    @field_validator("new_city")
    @classmethod
    def check_new_city(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("new_city is required")
        return value

    @field_validator("new_ward")
    @classmethod
    def check_new_ward(cls, value: Any) -> Any:
        if value is None or value == "":
            raise ValueError("new_ward is required")
        return value


class DescriptionResponse(SchemaBase):
    title: str | None = Field(description="Title")
    description: str | None = Field(description="Description")
    usage: RemainResponse | None = Field(description="Usage Information")


class PairAddressDescriptionResponse(SchemaBase):
    title: str | None = Field(description="Title")
    description: str | None = Field(description="Description")
    usage: RemainResponse | None = Field(description="Usage Information")
