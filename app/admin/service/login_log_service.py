#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi import Request
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.crud.crud_login_log import login_log_dao
from app.admin.schema.login_log import CreateLoginLogParam
from common.log import log
from database.db import AsyncSessionLocal


class LoginLogService:
    """Login Log Service Class"""

    @staticmethod
    async def get_select(
        *, username: str | None, status: int | None, ip: str | None
    ) -> Select:
        """
        Get login log list query conditions

        :param username: Username
        :param status: Status
        :param ip: IP address
        :return:
        """
        return await login_log_dao.get_list(username=username, status=status, ip=ip)

    @staticmethod
    async def create(
        *,
        db: AsyncSession,
        request: Request,
        user_uuid: str,
        username: str,
        login_time: datetime,
        status: int,
        msg: str,
    ) -> None:
        """
        Create login log

        :param db: Database session
        :param request: FastAPI request object
        :param user_uuid: User UUID
        :param username: Username
        :param login_time: Login time
        :param status: Status
        :param msg: Message
        :return:
        """
        try:
            obj = CreateLoginLogParam(
                user_uuid=user_uuid,
                username=username,
                status=status,
                ip=request.state.ip,
                country=request.state.country,
                region=request.state.region,
                city=request.state.city,
                user_agent=request.state.user_agent,
                browser=request.state.browser,
                os=request.state.os,
                device=request.state.device,
                msg=msg,
                login_time=login_time,
            )
            await login_log_dao.create(db, obj)
        except Exception as e:
            log.error(f"Failed to create login log: {e}")

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        """
        Delete login log

        :param pk: Log ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            count = await login_log_dao.delete(db, pk)
            return count

    @staticmethod
    async def delete_all() -> int:
        """Clear all login logs"""
        async with AsyncSessionLocal.begin() as db:
            count = await login_log_dao.delete_all(db)
            return count


login_log_service: LoginLogService = LoginLogService()
