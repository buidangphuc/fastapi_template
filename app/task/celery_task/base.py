#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
from typing import Any

from celery import Task
from sqlalchemy.exc import SQLAlchemyError

from app.task.conf import task_settings
from common.socketio.actions import task_notification


class TaskBase(Task):
    """Celery task base class"""

    autoretry_for = (SQLAlchemyError,)
    max_retries = task_settings.CELERY_TASK_MAX_RETRIES

    async def before_start(self, task_id: str, args, kwargs) -> None:
        """
        Hook executed before the task starts

        :param task_id: Task ID
        :return:
        """
        await task_notification(msg=f"Task {task_id} started")

    async def on_success(self, retval: Any, task_id: str, args, kwargs) -> None:
        """
        Hook executed after the task succeeds

        :param retval: Task return value
        :param task_id: Task ID
        :return:
        """
        await task_notification(msg=f"Task {task_id} executed successfully")

    def on_failure(self, exc: Exception, task_id: str, args, kwargs, einfo) -> None:
        """
        Hook executed after the task fails

        :param exc: Exception object
        :param task_id: Task ID
        :param einfo: Exception information
        :return:
        """
        loop = asyncio.get_event_loop()
        loop.create_task(task_notification(msg=f"Task {task_id} execution failed"))
