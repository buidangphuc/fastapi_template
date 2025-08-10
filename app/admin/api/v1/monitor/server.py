#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from common.response.response_schema import ResponseModel, response_base
from common.security.jwt import DependsJwtAuth
from common.security.permission import RequestPermission
from utils.server_info import server_info

router = APIRouter()


@router.get(
    "",
    summary="server monitoring",
    dependencies=[
        Depends(RequestPermission("sys:monitor:server")),
        DependsJwtAuth,
    ],
)
async def get_server_info() -> ResponseModel:
    data = {
        # Throw it into a thread pool to avoid blocking the event loop
        "cpu": await run_in_threadpool(server_info.get_cpu_info),
        "mem": await run_in_threadpool(server_info.get_mem_info),
        "sys": await run_in_threadpool(server_info.get_sys_info),
        "disk": await run_in_threadpool(server_info.get_disk_info),
        "service": await run_in_threadpool(server_info.get_service_info),
    }
    return response_base.success(data=data)
