#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select

from app.admin.crud.crud_data_rule import data_rule_dao
from app.admin.crud.crud_menu import menu_dao
from app.admin.crud.crud_role import role_dao
from app.admin.model import Role
from app.admin.schema.role import (
    CreateRoleParam,
    UpdateRoleMenuParam,
    UpdateRoleParam,
    UpdateRoleRuleParam,
)
from common.exception import errors
from core.conf import settings
from database.db import AsyncSessionLocal
from database.redis import redis_client


class RoleService:
    """Role Service Class"""

    @staticmethod
    async def get(*, pk: int) -> Role:
        """
        Get role details

        :param pk: Role ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            role = await role_dao.get_with_relation(db, pk)
            if not role:
                raise errors.NotFoundError(msg='Role does not exist')
            return role

    @staticmethod
    async def get_all() -> Sequence[Role]:
        """Get all roles"""
        async with AsyncSessionLocal() as db:
            roles = await role_dao.get_all(db)
            return roles

    @staticmethod
    async def get_by_user(*, pk: int) -> Sequence[Role]:
        """
        Get user's role list

        :param pk: User ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            roles = await role_dao.get_by_user(db, user_id=pk)
            return roles

    @staticmethod
    async def get_select(*, name: str | None, status: int | None) -> Select:
        """
        Get role list query conditions

        :param name: Role name
        :param status: Status
        :return:
        """
        return await role_dao.get_list(name=name, status=status)

    @staticmethod
    async def create(*, obj: CreateRoleParam) -> None:
        """
        Create role

        :param obj: Role creation parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            role = await role_dao.get_by_name(db, obj.name)
            if role:
                raise errors.ForbiddenError(msg='Role already exists')
            await role_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateRoleParam) -> int:
        """
        Update role

        :param pk: Role ID
        :param obj: Role update parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            role = await role_dao.get(db, pk)
            if not role:
                raise errors.NotFoundError(msg='Role does not exist')
            if role.name != obj.name:
                role = await role_dao.get_by_name(db, obj.name)
                if role:
                    raise errors.ForbiddenError(msg='Role already exists')
            count = await role_dao.update(db, pk, obj)
            for user in await role.awaitable_attrs.users:
                await redis_client.delete_prefix(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
            return count

    @staticmethod
    async def update_role_menu(*, pk: int, menu_ids: UpdateRoleMenuParam) -> int:
        """
        Update role menu

        :param pk: Role ID
        :param menu_ids: Menu ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            role = await role_dao.get_with_relation(db, pk)
            if not role:
                raise errors.NotFoundError(msg='Role does not exist')
            for menu_id in menu_ids.menus:
                menu = await menu_dao.get(db, menu_id)
                if not menu:
                    raise errors.NotFoundError(msg='Menu does not exist')
            count = await role_dao.update_menus(db, pk, menu_ids)
            for user in await role.awaitable_attrs.users:
                await redis_client.delete_prefix(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
            return count

    @staticmethod
    async def update_role_rule(*, pk: int, rule_ids: UpdateRoleRuleParam) -> int:
        """
        Update role data rules

        :param pk: Role ID
        :param rule_ids: Permission rule ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            role = await role_dao.get(db, pk)
            if not role:
                raise errors.NotFoundError(msg='Role does not exist')
            for rule_id in rule_ids.rules:
                rule = await data_rule_dao.get(db, rule_id)
                if not rule:
                    raise errors.NotFoundError(msg='Data rule does not exist')
            count = await role_dao.update_rules(db, pk, rule_ids)
            for user in await role.awaitable_attrs.users:
                await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        """
        Delete role

        :param pk: Role ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            count = await role_dao.delete(db, pk)
            for _pk in pk:
                role = await role_dao.get(db, _pk)
                if role:
                    for user in await role.awaitable_attrs.users:
                        await redis_client.delete(f'{settings.JWT_USER_REDIS_PREFIX}:{user.id}')
            return count


role_service: RoleService = RoleService()
