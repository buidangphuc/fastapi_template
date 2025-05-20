#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from pydantic import Field

from app.admin.schema.user import GetUserInfoDetail
from common.enums import StatusType
from common.schema import SchemaBase


class GetSwaggerToken(SchemaBase):
    """Swagger Authentication Token"""

    access_token: str = Field(description='Access Token')
    token_type: str = Field('Bearer', description='Token Type')
    user: GetUserInfoDetail = Field(description='User Information')


class AccessTokenBase(SchemaBase):
    """Access Token Base Model"""

    access_token: str = Field(description='Access Token')
    access_token_expire_time: datetime = Field(description='Token Expiration Time')
    session_uuid: str = Field(description='Session UUID')


class GetNewToken(AccessTokenBase):
    """Get New Token"""


class GetLoginToken(AccessTokenBase):
    """Get Login Token"""

    user: GetUserInfoDetail = Field(description='User Information')


class KickOutToken(SchemaBase):
    """Kick Out Token"""

    session_uuid: str = Field(description='Session UUID')


class GetTokenDetail(SchemaBase):
    """Token Details"""

    id: int = Field(description='User ID')
    session_uuid: str = Field(description='Session UUID')
    username: str = Field(description='Username')
    nickname: str = Field(description='Nickname')
    ip: str = Field(description='IP Address')
    os: str = Field(description='Operating System')
    browser: str = Field(description='Browser')
    device: str = Field(description='Device')
    status: StatusType = Field(description='Status')
    last_login_time: str = Field(description='Last Login Time')
    expire_time: datetime = Field(description='Expiration Time')
