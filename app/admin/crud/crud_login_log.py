#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from app.admin.model import LoginLog
from app.admin.schema.login_log import CreateLoginLogParam


class CRUDLoginLog(CRUDPlus[LoginLog]):
    """CRUD for LoginLog model."""

    async def get_list(
        self, username: str | None, status: int | None, ip: str | None
    ) -> Select:
        filters = {}
        if username is not None:
            filters.update(username__like=f"%{username}%")
        if status is not None:
            filters.update(status=status)
        if ip is not None:
            filters.update(ip__like=f"%{ip}%")
        return await self.select_order("created_time", "desc", **filters)

    async def create(self, db: AsyncSession, obj: CreateLoginLogParam) -> None:

        await self.create_model(db, obj, commit=True)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:

        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def delete_all(self, db: AsyncSession) -> int:

        return await self.delete_model_by_column(db, allow_multiple=True)


login_log_dao: CRUDLoginLog = CRUDLoginLog(LoginLog)
