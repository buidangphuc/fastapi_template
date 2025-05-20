#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from app.admin.schema.data_rule import GetDataRuleDetail
from app.admin.schema.menu import GetMenuDetail
from common.enums import StatusType
from common.schema import SchemaBase


class RoleSchemaBase(SchemaBase):
    """Role Base Model"""

    name: str = Field(description='Role Name')
    status: StatusType = Field(StatusType.enable, description='Status')
    remark: str | None = Field(None, description='Remark')


class CreateRoleParam(RoleSchemaBase):
    """Create Role Parameters"""


class UpdateRoleParam(RoleSchemaBase):
    """Update Role Parameters"""


class UpdateRoleMenuParam(SchemaBase):
    """Update Role Menu Parameters"""

    menus: list[int] = Field(description='Menu ID List')


class UpdateRoleRuleParam(SchemaBase):
    """Update Role Rule Parameters"""

    rules: list[int] = Field(description='Data Rule ID List')


class GetRoleDetail(RoleSchemaBase):
    """Role Details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Role ID')
    created_time: datetime = Field(description='Creation Time')
    updated_time: datetime | None = Field(None, description='Update Time')


class GetRoleWithRelationDetail(GetRoleDetail):
    """Role with Relation Details"""

    menus: list[GetMenuDetail | None] = Field([], description='Menu Detail List')
    rules: list[GetDataRuleDetail | None] = Field([], description='Data Rule Detail List')
