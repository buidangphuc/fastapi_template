#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any

from pydantic import Field

from common.schema import SchemaBase


class RunParam(SchemaBase):
    """Task run parameters"""

    name: str = Field(description='Task name')
    args: list[Any] | None = Field(None, description='Task function positional arguments')
    kwargs: dict[str, Any] | None = Field(None, description='Task function keyword arguments')


class TaskResult(SchemaBase):
    """Task execution results"""

    result: str = Field(description='Task execution result')
    traceback: str = Field(description='Error stack information')
    status: str = Field(description='Task status')
    name: str = Field(description='Task name')
    args: list[Any] | None = Field(None, description='Task function positional arguments')
    kwargs: dict[str, Any] | None = Field(None, description='Task function keyword arguments')
    worker: str = Field(description='Worker executing the task')
    retries: int | None = Field(None, description='Retry count')
    queue: str | None = Field(None, description='Task queue')
