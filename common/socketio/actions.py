#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from common.socketio.server import sio


async def task_notification(msg: str):
    """
    Task notification

    :param msg: Notification message
    :return:
    """
    await sio.emit('task_notification', {'msg': msg})
