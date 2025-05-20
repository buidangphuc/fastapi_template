#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from app.admin.api.v1.auth import router as auth_router
from app.admin.api.v1.log import router as log_router
from app.admin.api.v1.monitor import router as monitor_router
from app.admin.api.v1.sys import router as sys_router
from core.conf import settings

v1 = APIRouter(prefix=settings.FASTAPI_API_V1_PATH)

v1.include_router(auth_router)
v1.include_router(sys_router)
v1.include_router(log_router)
v1.include_router(monitor_router)
