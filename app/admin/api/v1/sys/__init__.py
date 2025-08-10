#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from app.admin.api.v1.sys.data_rule import router as data_rule_router
from app.admin.api.v1.sys.dept import router as dept_router
from app.admin.api.v1.sys.menu import router as menu_router
from app.admin.api.v1.sys.role import router as role_router
from app.admin.api.v1.sys.token import router as token_router
from app.admin.api.v1.sys.upload import router as upload_router
from app.admin.api.v1.sys.user import router as user_router

router = APIRouter(prefix="/sys")

router.include_router(dept_router, prefix="/depts", tags=["sys department"])
router.include_router(menu_router, prefix="/menus", tags=["sys menu"])
router.include_router(role_router, prefix="/roles", tags=["sys role"])
router.include_router(user_router, prefix="/users", tags=["sys user"])
router.include_router(data_rule_router, prefix="/data-rules", tags=["sys data rule"])
router.include_router(token_router, prefix="/tokens", tags=["sys token"])
router.include_router(upload_router, prefix="/upload", tags=["sys upload"])
