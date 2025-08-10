#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from common.enums import StatusType
from common.schema import CustomEmailStr, CustomPhoneNumber, SchemaBase


class DeptSchemaBase(SchemaBase):
    """Department schema base"""

    name: str = Field(description="department name")
    parent_id: int | None = Field(None, description="parent ID")
    sort: int = Field(0, ge=0, description="sort order")
    leader: str | None = Field(None, description="leader name")
    phone: CustomPhoneNumber | None = Field(None, description="leader phone")
    email: CustomEmailStr | None = Field(None, description="leader email")
    status: StatusType = Field(
        StatusType.enable, description="status (0: enable, 1: disable)"
    )


class CreateDeptParam(DeptSchemaBase):
    """Create department parameters"""


class UpdateDeptParam(DeptSchemaBase):
    """Update department parameters"""


class GetDeptDetail(DeptSchemaBase):
    """Get department details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="department ID")
    del_flag: bool = Field(description="deleted flag")
    created_time: datetime = Field(description="creation time")
    updated_time: datetime | None = Field(None, description="update time")
