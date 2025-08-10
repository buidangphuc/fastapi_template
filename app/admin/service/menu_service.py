#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any

from fastapi import Request

from app.admin.crud.crud_menu import menu_dao
from app.admin.crud.crud_role import role_dao
from app.admin.model import Menu
from app.admin.schema.menu import CreateMenuParam, UpdateMenuParam
from common.exception import errors
from core.conf import settings
from database.db import AsyncSessionLocal
from database.redis import redis_client
from utils.build_tree import get_tree_data, get_vben5_tree_data


class MenuService:
    """Menu Service Class"""

    @staticmethod
    async def get(*, pk: int) -> Menu:
        """
        Get menu details

        :param pk: Menu ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            menu = await menu_dao.get(db, menu_id=pk)
            if not menu:
                raise errors.NotFoundError(msg="Menu does not exist")
            return menu

    @staticmethod
    async def get_menu_tree(
        *, title: str | None, status: int | None
    ) -> list[dict[str, Any]]:
        """
        Get menu tree structure

        :param title: Menu title
        :param status: Status
        :return:
        """
        async with AsyncSessionLocal() as db:
            menu_select = await menu_dao.get_all(db, title=title, status=status)
            menu_tree = get_tree_data(menu_select)
            return menu_tree

    @staticmethod
    async def get_role_menu_tree(*, pk: int) -> list[dict[str, Any]]:
        """
        Get role menu tree structure

        :param pk: Role ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            role = await role_dao.get_with_relation(db, pk)
            if not role:
                raise errors.NotFoundError(msg="Role does not exist")
            menu_ids = [menu.id for menu in role.menus]
            menu_select = await menu_dao.get_role_menus(db, False, menu_ids)
            menu_tree = get_tree_data(menu_select)
            return menu_tree

    @staticmethod
    async def get_user_menu_tree(*, request: Request) -> list[dict[str, Any]]:
        """
        Get user menu tree structure

        :param request: FastAPI request object
        :return:
        """
        async with AsyncSessionLocal() as db:
            roles = request.user.roles
            menu_ids = []
            menu_tree = []
            if roles:
                for role in roles:
                    menu_ids.extend([menu.id for menu in role.menus])
                menu_select = await menu_dao.get_role_menus(
                    db, request.user.is_superuser, menu_ids
                )
                menu_tree = get_vben5_tree_data(menu_select)
            return menu_tree

    @staticmethod
    async def create(*, obj: CreateMenuParam) -> None:
        """
        Create menu

        :param obj: Menu creation parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            title = await menu_dao.get_by_title(db, obj.title)
            if title:
                raise errors.ForbiddenError(msg="Menu title already exists")
            if obj.parent_id:
                parent_menu = await menu_dao.get(db, obj.parent_id)
                if not parent_menu:
                    raise errors.NotFoundError(msg="Parent menu does not exist")
            await menu_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateMenuParam) -> int:
        """
        Update menu

        :param pk: Menu ID
        :param obj: Menu update parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            menu = await menu_dao.get(db, pk)
            if not menu:
                raise errors.NotFoundError(msg="Menu does not exist")
            if menu.title != obj.title:
                if await menu_dao.get_by_title(db, obj.title):
                    raise errors.ForbiddenError(msg="Menu title already exists")
            if obj.parent_id:
                parent_menu = await menu_dao.get(db, obj.parent_id)
                if not parent_menu:
                    raise errors.NotFoundError(msg="Parent menu does not exist")
            if obj.parent_id == menu.id:
                raise errors.ForbiddenError(msg="Cannot associate itself as a parent")
            count = await menu_dao.update(db, pk, obj)
            for role in await menu.awaitable_attrs.roles:
                for user in await role.awaitable_attrs.users:
                    await redis_client.delete(
                        f"{settings.JWT_USER_REDIS_PREFIX}:{user.id}"
                    )
            return count

    @staticmethod
    async def delete(*, pk: int) -> int:
        """
        Delete menu

        :param pk: Menu ID
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            children = await menu_dao.get_children(db, pk)
            if children:
                raise errors.ForbiddenError(msg="Menu has sub-menus, cannot delete")
            menu = await menu_dao.get(db, pk)
            count = await menu_dao.delete(db, pk)
            if menu:
                for role in await menu.awaitable_attrs.roles:
                    for user in await role.awaitable_attrs.users:
                        await redis_client.delete(
                            f"{settings.JWT_USER_REDIS_PREFIX}:{user.id}"
                        )
            return count


menu_service: MenuService = MenuService()
