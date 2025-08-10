#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import timedelta
from typing import Any
from uuid import uuid4

from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import ExpiredSignatureError, JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic_core import from_json
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.model import User
from app.admin.schema.user import GetUserInfoWithRelationDetail
from common.dataclasses import AccessToken, NewToken, RefreshToken, TokenPayload
from common.exception.errors import AuthorizationError, TokenError
from core.conf import settings
from database.db import AsyncSessionLocal
from database.redis import redis_client
from utils.serializers import select_as_dict
from utils.timezone import timezone

# JWT authorizes dependency injection
DependsJwtAuth = Depends(HTTPBearer())

password_hash = PasswordHash((BcryptHasher(),))


def get_hash_password(password: str, salt: bytes | None) -> str:
    """
    Encrypt password using hash algorithm

    :param password: Password
    :param salt: Salt value
    :return:
    """
    return password_hash.hash(password, salt=salt)


def password_verify(plain_password: str, hashed_password: str) -> bool:
    """
    Password verification

    :param plain_password: Password to verify
    :param hashed_password: Hashed password
    :return:
    """
    return password_hash.verify(plain_password, hashed_password)


def jwt_encode(payload: dict[str, Any]) -> str:
    """
    Generate JWT token

    :param payload: Payload
    :return:
    """
    return jwt.encode(
        payload,
        settings.TOKEN_SECRET_KEY,
        settings.TOKEN_ALGORITHM,
    )


def jwt_decode(token: str) -> TokenPayload:
    """
    Decode JWT token

    :param token: JWT token
    :return:
    """
    try:
        payload = jwt.decode(
            token, settings.TOKEN_SECRET_KEY, algorithms=[settings.TOKEN_ALGORITHM]
        )
        session_uuid = payload.get("session_uuid") or "debug"
        user_id = payload.get("sub")
        expire_time = payload.get("exp")
        if not user_id:
            raise TokenError(msg="Invalid token")
    except ExpiredSignatureError:
        raise TokenError(msg="Token has expired")
    except (JWTError, Exception):
        raise TokenError(msg="Invalid token")
    return TokenPayload(
        id=int(user_id), session_uuid=session_uuid, expire_time=expire_time
    )


async def create_access_token(user_id: str, multi_login: bool, **kwargs) -> AccessToken:
    """
    Generate encrypted token

    :param user_id: User ID
    :param multi_login: Whether to allow multi-device login
    :param kwargs: Additional token information
    :return:
    """
    expire = timezone.now() + timedelta(seconds=settings.TOKEN_EXPIRE_SECONDS)
    session_uuid = str(uuid4())
    access_token = jwt_encode(
        {
            "session_uuid": session_uuid,
            "exp": expire,
            "sub": user_id,
        }
    )

    if not multi_login:
        await redis_client.delete_prefix(f"{settings.TOKEN_REDIS_PREFIX}:{user_id}")

    await redis_client.setex(
        f"{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}",
        settings.TOKEN_EXPIRE_SECONDS,
        access_token,
    )

    # Additional token information is stored separately
    if kwargs:
        await redis_client.setex(
            f"{settings.TOKEN_EXTRA_INFO_REDIS_PREFIX}:{session_uuid}",
            settings.TOKEN_EXPIRE_SECONDS,
            json.dumps(kwargs, ensure_ascii=False),
        )

    return AccessToken(
        access_token=access_token,
        access_token_expire_time=expire,
        session_uuid=session_uuid,
    )


async def create_refresh_token(user_id: str, multi_login: bool) -> RefreshToken:
    """
    Generate encrypted refresh token, only used to create new tokens

    :param user_id: User ID
    :param multi_login: Whether to allow multi-device login
    :return:
    """
    expire = timezone.now() + timedelta(seconds=settings.TOKEN_REFRESH_EXPIRE_SECONDS)
    refresh_token = jwt_encode({"exp": expire, "sub": user_id})

    if not multi_login:
        key_prefix = f"{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}"
        await redis_client.delete_prefix(key_prefix)

    await redis_client.setex(
        f"{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{refresh_token}",
        settings.TOKEN_REFRESH_EXPIRE_SECONDS,
        refresh_token,
    )
    return RefreshToken(refresh_token=refresh_token, refresh_token_expire_time=expire)


async def create_new_token(
    user_id: str, refresh_token: str, multi_login: bool, **kwargs
) -> NewToken:
    """
    Generate new token

    :param user_id: User ID
    :param refresh_token: Refresh token
    :param multi_login: Whether to allow multi-device login
    :param kwargs: Additional token information
    :return:
    """
    redis_refresh_token = await redis_client.get(
        f"{settings.TOKEN_REFRESH_REDIS_PREFIX}:{user_id}:{refresh_token}"
    )
    if not redis_refresh_token or redis_refresh_token != refresh_token:
        raise TokenError(msg="Refresh Token has expired, please login again")
    new_access_token = await create_access_token(user_id, multi_login, **kwargs)
    return NewToken(
        new_access_token=new_access_token.access_token,
        new_access_token_expire_time=new_access_token.access_token_expire_time,
        session_uuid=new_access_token.session_uuid,
    )


async def revoke_token(user_id: str, session_uuid: str) -> None:
    """
    Revoke token

    :param user_id: User ID
    :param session_uuid: Session ID
    :return:
    """
    token_key = f"{settings.TOKEN_REDIS_PREFIX}:{user_id}:{session_uuid}"
    await redis_client.delete(token_key)


def get_token(request: Request) -> str:
    """
    Get token from request header

    :param request: FastAPI request object
    :return:
    """
    authorization = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        raise TokenError(msg="Invalid token")
    return token


async def get_current_user(db: AsyncSession, pk: int) -> User:
    """
    Get current user

    :param db: Database session
    :param pk: User ID
    :return:
    """
    from app.admin.crud.crud_user import user_dao

    user = await user_dao.get_with_relation(db, user_id=pk)
    if not user:
        raise TokenError(msg="Invalid token")
    if not user.status:
        raise AuthorizationError(
            msg="User is locked, please contact system administrator"
        )
    if user.dept_id:
        if not user.dept.status:
            raise AuthorizationError(
                msg="User's department is locked, please contact system administrator"
            )
        if user.dept.del_flag:
            raise AuthorizationError(
                msg="User's department has been deleted, please contact system administrator"
            )
    if user.roles:
        role_status = [role.status for role in user.roles]
        if all(status == 0 for status in role_status):
            raise AuthorizationError(
                msg="User's roles are locked, please contact system administrator"
            )
    return user


def superuser_verify(request: Request) -> bool:
    """
    Verify current user permissions

    :param request: FastAPI request object
    :return:
    """
    superuser = request.user.is_superuser
    if not superuser or not request.user.is_staff:
        raise AuthorizationError
    return superuser


async def jwt_authentication(token: str) -> GetUserInfoWithRelationDetail:
    """
    JWT authentication

    :param token: JWT token
    :return:
    """
    token_payload = jwt_decode(token)
    user_id = token_payload.id
    redis_token = await redis_client.get(
        f"{settings.TOKEN_REDIS_PREFIX}:{user_id}:{token_payload.session_uuid}"
    )
    if not redis_token:
        raise TokenError(msg="Token has expired")

    if token != redis_token:
        raise TokenError(msg="Token is invalid")

    cache_user = await redis_client.get(f"{settings.JWT_USER_REDIS_PREFIX}:{user_id}")
    if not cache_user:
        async with AsyncSessionLocal() as db:
            current_user = await get_current_user(db, user_id)
            user = GetUserInfoWithRelationDetail(**select_as_dict(current_user))
            await redis_client.setex(
                f"{settings.JWT_USER_REDIS_PREFIX}:{user_id}",
                settings.JWT_USER_REDIS_EXPIRE_SECONDS,
                user.model_dump_json(),
            )
    else:
        user = GetUserInfoWithRelationDetail.model_validate(
            from_json(cache_user, allow_partial=True)
        )
    return user
