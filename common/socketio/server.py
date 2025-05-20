#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import socketio

from app.task.conf import task_settings
from common.log import log
from common.security.jwt import jwt_authentication
from core.conf import settings
from database.redis import redis_client

# Create Socket.IO server instance
sio = socketio.AsyncServer(
    # Integrate Celery to implement message subscription
    client_manager=socketio.AsyncRedisManager(
        f'redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:'
        f'{settings.REDIS_PORT}/{task_settings.CELERY_BROKER_REDIS_DATABASE}'
    )
    if task_settings.CELERY_BROKER == 'redis'
    else socketio.AsyncAioPikaManager(
        (
            f'amqp://{task_settings.RABBITMQ_USERNAME}:{task_settings.RABBITMQ_PASSWORD}@'
            f'{task_settings.RABBITMQ_HOST}:{task_settings.RABBITMQ_PORT}'
        )
    ),
    async_mode='asgi',
    cors_allowed_origins=settings.CORS_ALLOWED_ORIGINS,
    cors_credentials=True,
    namespaces=['/ws'],
)


@sio.event
async def connect(sid, environ, auth):
    """Handle WebSocket connection event"""
    if not auth:
        log.error('WebSocket connection failed: No authorization')
        return False

    session_uuid = auth.get('session_uuid')
    token = auth.get('token')
    if not token or not session_uuid:
        log.error('WebSocket connection failed: Authorization failed, please check')
        return False

    # Direct connection without authorization
    if token == settings.WS_NO_AUTH_MARKER:
        await redis_client.sadd(settings.TOKEN_ONLINE_REDIS_PREFIX, session_uuid)
        return True

    try:
        await jwt_authentication(token)
    except Exception as e:
        log.info(f'WebSocket connection failed: {str(e)}')
        return False

    await redis_client.sadd(settings.TOKEN_ONLINE_REDIS_PREFIX, session_uuid)
    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle WebSocket disconnection event"""
    await redis_client.spop(settings.TOKEN_ONLINE_REDIS_PREFIX)
