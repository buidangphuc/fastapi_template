#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from common.enums import RoleDataRuleExpressionType, RoleDataRuleOperatorType
from common.schema import SchemaBase


class DataRuleSchemaBase(SchemaBase):
    """Base schema for data rules"""

    name: str = Field(description="rule name")
    model: str = Field(description="rule model name")
    column: str = Field(description="rule column name")
    operator: RoleDataRuleOperatorType = Field(
        RoleDataRuleOperatorType.OR, description="Operator (OR, AND)"
    )
    expression: RoleDataRuleExpressionType = Field(
        RoleDataRuleExpressionType.eq, description="rule expression type"
    )
    value: str = Field(description="rule value")


class CreateDataRuleParam(DataRuleSchemaBase):
    """Create data rule parameters"""


class UpdateDataRuleParam(DataRuleSchemaBase):
    """Update data rule parameters"""


class GetDataRuleDetail(DataRuleSchemaBase):
    """Get data rule details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="rule ID")
    created_time: datetime = Field(description="creation time")
    updated_time: datetime | None = Field(None, description="update time")

    def __hash__(self) -> int:
        """Override the hash function to use the name of the data rule."""
        return hash(self.name)
