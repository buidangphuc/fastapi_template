#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from app.admin.api.v1.auth.auth import router as auth_router

router = APIRouter(prefix='/auth')

router.include_router(auth_router, tags=['auth'])
