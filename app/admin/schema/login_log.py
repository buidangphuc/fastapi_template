#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import ConfigDict, Field

from common.schema import SchemaBase


class LoginLogSchemaBase(SchemaBase):
    """Login log schema base"""

    user_uuid: str = Field(description="user UUID")
    username: str = Field(description="username")
    status: int = Field(description="status")
    ip: str = Field(description="IP address")
    country: str | None = Field(None, description="country")
    region: str | None = Field(None, description="region")
    city: str | None = Field(None, description="city")
    user_agent: str = Field(description="user agent")
    browser: str | None = Field(None, description="browser")
    os: str | None = Field(None, description="os")
    device: str | None = Field(None, description="device")
    msg: str = Field(description="message")
    login_time: datetime = Field(description="login time")


class CreateLoginLogParam(LoginLogSchemaBase):
    """Create login log parameters"""


class UpdateLoginLogParam(LoginLogSchemaBase):
    """Update login log parameters"""


class GetLoginLogDetail(LoginLogSchemaBase):
    """Get login log details"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="log ID")
    created_time: datetime = Field(description="creation time")
