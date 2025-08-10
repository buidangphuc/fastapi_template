#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload
from sqlalchemy_crud_plus import CRUDPlus

from app.admin.model import DataRule, Menu, Role, User
from app.admin.schema.role import (
    CreateRoleParam,
    UpdateRoleMenuParam,
    UpdateRoleParam,
    UpdateRoleRuleParam,
)


class CRUDRole(CRUDPlus[Role]):
    """CRUD for Role model."""

    async def get(self, db: AsyncSession, role_id: int) -> Role | None:

        return await self.select_model(db, role_id)

    async def get_with_relation(self, db: AsyncSession, role_id: int) -> Role | None:

        stmt = (
            select(self.model)
            .options(selectinload(self.model.menus), selectinload(self.model.rules))
            .where(self.model.id == role_id)
        )
        role = await db.execute(stmt)
        return role.scalars().first()

    async def get_all(self, db: AsyncSession) -> Sequence[Role]:

        return await self.select_models(db)

    async def get_by_user(self, db: AsyncSession, user_id: int) -> Sequence[Role]:

        stmt = select(self.model).join(self.model.users).where(User.id == user_id)
        roles = await db.execute(stmt)
        return roles.scalars().all()

    async def get_list(self, name: str | None, status: int | None) -> Select:

        stmt = (
            select(self.model)
            .options(
                noload(self.model.users),
                noload(self.model.menus),
                noload(self.model.rules),
            )
            .order_by(desc(self.model.created_time))
        )

        filters = []
        if name is not None:
            filters.append(self.model.name.like(f"%{name}%"))
        if status is not None:
            filters.append(self.model.status == status)

        if filters:
            stmt = stmt.where(and_(*filters))

        return stmt

    async def get_by_name(self, db: AsyncSession, name: str) -> Role | None:

        return await self.select_model_by_column(db, name=name)

    async def create(self, db: AsyncSession, obj: CreateRoleParam) -> None:

        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, role_id: int, obj: UpdateRoleParam) -> int:

        return await self.update_model(db, role_id, obj)

    async def update_menus(
        self, db: AsyncSession, role_id: int, menu_ids: UpdateRoleMenuParam
    ) -> int:

        current_role = await self.get_with_relation(db, role_id)
        stmt = select(Menu).where(Menu.id.in_(menu_ids.menus))
        menus = await db.execute(stmt)
        current_role.menus = menus.scalars().all()
        return len(current_role.menus)

    async def update_rules(
        self, db: AsyncSession, role_id: int, rule_ids: UpdateRoleRuleParam
    ) -> int:

        current_role = await self.get_with_relation(db, role_id)
        stmt = select(DataRule).where(DataRule.id.in_(rule_ids.rules))
        rules = await db.execute(stmt)
        current_role.rules = rules.scalars().all()
        return len(current_role.rules)

    async def delete(self, db: AsyncSession, role_id: list[int]) -> int:

        return await self.delete_model_by_column(
            db, allow_multiple=True, id__in=role_id
        )


role_dao: CRUDRole = CRUDRole(Role)
