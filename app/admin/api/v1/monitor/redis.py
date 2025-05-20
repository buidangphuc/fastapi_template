#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends

from common.response.response_schema import ResponseModel, response_base
from common.security.jwt import DependsJwtAuth
from common.security.permission import RequestPermission
from utils.redis_info import redis_info

router = APIRouter()


@router.get(
    '',
    summary='redis monitoring',
    dependencies=[
        Depends(RequestPermission('sys:monitor:redis')),
        DependsJwtAuth,
    ],
)
async def get_redis_info() -> ResponseModel:
    data = {
        'info': await redis_info.get_info(),
        'stats': await redis_info.get_stats(),
    }
    return response_base.success(data=data)
