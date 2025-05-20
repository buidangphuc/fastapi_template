#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from common.enums import MenuType, StatusType
from common.schema import SchemaBase


class MenuSchemaBase(SchemaBase):
    """Menu schema base"""

    title: str = Field(description='Menu Title')
    name: str = Field(description='Menu Name')
    path: str = Field(description='Route Path')
    parent_id: int | None = Field(None, description='Parent Menu ID')
    sort: int = Field(0, ge=0, description='Sort Order')
    icon: str | None = Field(None, description='Icon')
    type: MenuType = Field(MenuType.directory, description='Menu Type (0 Directory, 1 Menu, 2 Button)')
    component: str | None = Field(None, description='Component Path')
    perms: str | None = Field(None, description='Permission Identifier')
    status: StatusType = Field(StatusType.enable, description='Status')
    display: StatusType = Field(StatusType.enable, description='Display Status')
    cache: StatusType = Field(StatusType.enable, description='Cache Status')
    link: str | None = Field(None, description='External Link')
    remark: str | None = Field(None, description='Remark')


class CreateMenuParam(MenuSchemaBase):
    """Create Menu Parameters"""


class UpdateMenuParam(MenuSchemaBase):
    """Update Menu Parameters"""


class GetMenuDetail(MenuSchemaBase):
    """Menu Details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description='Menu ID')
    created_time: datetime = Field(description='Creation Time')
    updated_time: datetime | None = Field(None, description='Update Time')
