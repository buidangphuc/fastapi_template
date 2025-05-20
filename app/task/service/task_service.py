#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from celery.exceptions import NotRegistered
from celery.result import AsyncResult
from starlette.concurrency import run_in_threadpool

from app.task.celery import celery_app
from app.task.schema.task import RunParam, TaskResult
from common.exception import errors
from common.exception.errors import NotFoundError


class TaskService:
    @staticmethod
    async def get_list() -> list[str]:
        """Get list of all registered Celery tasks"""
        registered_tasks = await run_in_threadpool(celery_app.control.inspect().registered)
        if not registered_tasks:
            raise errors.ForbiddenError(msg='Celery service is not started')
        tasks = list(registered_tasks.values())[0]
        return tasks


    @staticmethod
    def revoke(*, tid: str) -> None:
        """
        Revoke a specific task

        :param tid: Task UUID
        :return:
        """
        try:
            result = AsyncResult(id=tid, app=celery_app)
        except NotRegistered:
            raise NotFoundError(msg='Task does not exist')
        result.revoke(terminate=True)

    @staticmethod
    def run(*, obj: RunParam) -> str:
        """
        Run a specific task

        :param obj: Task run parameters
        :return:
        """
        task: AsyncResult = celery_app.send_task(name=obj.name, args=obj.args, kwargs=obj.kwargs)
        return task.task_id


task_service: TaskService = TaskService()
