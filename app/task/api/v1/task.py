#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.task.schema.task import RunParam, TaskResult
from app.task.service.task_service import task_service
from common.response.response_schema import (
    ResponseModel,
    ResponseSchemaModel,
    response_base,
)
from common.security.jwt import DependsJwtAuth
from common.security.permission import RequestPermission
from common.security.rbac import DependsRBAC

router = APIRouter()


@router.get("", summary="Get executable tasks", dependencies=[DependsJwtAuth])
async def get_all_tasks() -> ResponseSchemaModel[list[str]]:
    tasks = await task_service.get_list()
    return response_base.success(data=tasks)


@router.post(
    "/{tid}",
    summary="Revoke task",
    dependencies=[
        Depends(RequestPermission("sys:task:revoke")),
        DependsRBAC,
    ],
)
async def revoke_task(
    tid: Annotated[str, Path(description="Task UUID")]
) -> ResponseModel:
    task_service.revoke(tid=tid)
    return response_base.success()


@router.post(
    "",
    summary="Execute task",
    dependencies=[
        Depends(RequestPermission("sys:task:run")),
        DependsRBAC,
    ],
)
async def run_task(obj: RunParam) -> ResponseSchemaModel[str]:
    task = task_service.run(obj=obj)
    return response_base.success(data=task)
