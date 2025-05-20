#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, EmailStr, Field, HttpUrl, model_validator
from typing_extensions import Self

from app.admin.schema.dept import GetDeptDetail
from app.admin.schema.role import GetRoleWithRelationDetail
from common.enums import StatusType
from common.schema import CustomPhoneNumber, SchemaBase


class AuthSchemaBase(SchemaBase):
    """User Authentication Base Model"""

    username: str = Field(description='Username')
    password: str | None = Field(description='Password')


class AuthLoginParam(AuthSchemaBase):
    """User Login Parameters"""

    captcha: str = Field(description='Verification Code')


class RegisterUserParam(AuthSchemaBase):
    """User Registration Parameters"""

    nickname: str | None = Field(None, description='Nickname')
    email: EmailStr = Field(examples=['user@example.com'], description='Email')


class AddUserParam(AuthSchemaBase):
    """Add User Parameters"""

    dept_id: int = Field(description='Department ID')
    roles: list[int] = Field(description='Role ID List')
    nickname: str | None = Field(None, description='Nickname')
    email: EmailStr = Field(examples=['user@example.com'], description='Email')


class ResetPasswordParam(SchemaBase):
    """Reset Password Parameters"""

    old_password: str = Field(description='Old Password')
    new_password: str = Field(description='New Password')
    confirm_password: str = Field(description='Confirm Password')


class UserInfoSchemaBase(SchemaBase):
    """User Information Base Model"""

    dept_id: int | None = Field(None, description='Department ID')
    username: str = Field(description='Username')
    nickname: str = Field(description='Nickname')
    email: EmailStr = Field(examples=['user@example.com'], description='Email')
    phone: CustomPhoneNumber | None = Field(None, description='Phone Number')


class UpdateUserParam(UserInfoSchemaBase):
    """Update User Parameters"""


class UpdateUserRoleParam(SchemaBase):
    """Update User Role Parameters"""

    roles: list[int] = Field(description='Role ID List')


class AvatarParam(SchemaBase):
    """Update Avatar Parameters"""

    url: HttpUrl = Field(description='Avatar HTTP Address')


class GetUserInfoDetail(UserInfoSchemaBase):
    """User Information Details"""

    model_config = ConfigDict(from_attributes=True)

    dept_id: int | None = Field(None, description='Department ID')
    id: int = Field(description='User ID')
    uuid: str = Field(description='User UUID')
    avatar: str | None = Field(None, description='Avatar')
    status: StatusType = Field(StatusType.enable, description='Status')
    is_superuser: bool = Field(description='Is Super Administrator')
    is_staff: bool = Field(description='Is Administrator')
    is_multi_login: bool = Field(description='Allow Multi-terminal Login')
    join_time: datetime = Field(description='Join Time')
    last_login_time: datetime | None = Field(None, description='Last Login Time')


class GetUserInfoWithRelationDetail(GetUserInfoDetail):
    """User Information with Relation Details"""

    model_config = ConfigDict(from_attributes=True)

    dept: GetDeptDetail | None = Field(None, description='Department Information')
    roles: list[GetRoleWithRelationDetail] = Field(description='Role List')


class GetCurrentUserInfoWithRelationDetail(GetUserInfoWithRelationDetail):
    """Current User Information with Relation Details"""

    model_config = ConfigDict(from_attributes=True)

    dept: str | None = Field(None, description='Department Name')
    roles: list[str] = Field(description='Role Name List')

    @model_validator(mode='before')
    @classmethod
    def handel(cls, data: Any) -> Self:
        """Process department and role data"""
        dept = data['dept']
        if dept:
            data['dept'] = dept['name']
        roles = data['roles']
        if roles:
            data['roles'] = [role['name'] for role in roles]
        return data
