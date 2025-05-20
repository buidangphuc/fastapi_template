#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from core.path_conf import BASE_PATH


class AdminSettings(BaseSettings):
    """Admin Configuration"""

    model_config = SettingsConfigDict(env_file=f'{BASE_PATH}/.env', env_file_encoding='utf-8', extra='ignore')



@lru_cache
def get_admin_settings() -> AdminSettings:
    """Get admin configuration"""
    return AdminSettings()


admin_settings = get_admin_settings()
