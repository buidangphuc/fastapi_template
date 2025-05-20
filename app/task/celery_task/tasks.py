#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from anyio import sleep

from app.task.celery import celery_app


@celery_app.task(name='task_demo_async')
async def task_demo_async() -> str:
    """Asynchronous example task, simulating time-consuming operations"""
    await sleep(20)
    return 'test async'
