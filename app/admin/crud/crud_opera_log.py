#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_crud_plus import CRUDPlus

from app.admin.model import OperaLog
from app.admin.schema.opera_log import CreateOperaLogParam


class CRUDOperaLogDao(CRUDPlus[OperaLog]):
    """CRUD for Operation Log model."""

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

    async def create(self, db: AsyncSession, obj: CreateOperaLogParam) -> None:

        await self.create_model(db, obj)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:

        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)

    async def delete_all(self, db: AsyncSession) -> int:

        return await self.delete_model_by_column(db, allow_multiple=True)


opera_log_dao: CRUDOperaLogDao = CRUDOperaLogDao(OperaLog)
