#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import Select

from app.admin.crud.crud_opera_log import opera_log_dao
from app.admin.schema.opera_log import CreateOperaLogParam
from database.db import AsyncSessionLocal


class OperaLogService:
    """Operation Log Service Class"""

    @staticmethod
    async def get_select(*, username: str | None, status: int | None, ip: str | None) -> Select:
        """
        Get operation log list query conditions

        :param username: Username
        :param status: Status
        :param ip: IP address
        :return:
        """
        return await opera_log_dao.get_list(username=username, status=status, ip=ip)

    @staticmethod
    async def create(*, obj: CreateOperaLogParam) -> None:
        """
        Create operation log

        :param obj: Operation log creation parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            await opera_log_dao.create(db, obj)

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        """
        Delete operation log

        :param pk: Log ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            count = await opera_log_dao.delete(db, pk)
            return count

    @staticmethod
    async def delete_all() -> int:
        """Clear all operation logs"""
        async with AsyncSessionLocal.begin() as db:
            count = await opera_log_dao.delete_all(db)
            return count


opera_log_service: OperaLogService = OperaLogService()
