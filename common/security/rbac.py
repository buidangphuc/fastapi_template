#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import Depends, Request

from common.enums import MethodType, StatusType
from common.exception import errors
from common.exception.errors import AuthorizationError, TokenError
from common.log import log
from common.security.jwt import DependsJwtAuth
from core.conf import settings
from utils.import_parse import import_module_cached


async def rbac_verify(request: Request, _token: str = DependsJwtAuth) -> None:
    """
    RBAC permission verification (authorization order is important, modify with caution)

    :param request: FastAPI request object
    :param _token: JWT token
    :return:
    """
    path = request.url.path

    # API authentication whitelist
    if path in settings.TOKEN_REQUEST_PATH_EXCLUDE:
        return

    # Mandatory JWT authorization status check
    if not request.auth.scopes:
        raise TokenError

    # Super admin is exempt from verification
    if request.user.is_superuser:
        return

    # Check user roles
    user_roles = request.user.roles
    if not user_roles or all(status == 0 for status in user_roles):
        raise AuthorizationError(
            msg="User has no assigned roles, please contact system administrator"
        )

    # Check user role menus
    if not any(len(role.menus) > 0 for role in user_roles):
        raise AuthorizationError(
            msg="User has no assigned menus, please contact system administrator"
        )

    # Check backend management operation permissions
    method = request.method
    if method != MethodType.GET or method != MethodType.OPTIONS:
        if not request.user.is_staff:
            raise AuthorizationError(
                msg="User is forbidden from backend operations, please contact system administrator"
            )

    # RBAC authorization
    if settings.RBAC_ROLE_MENU_MODE:
        path_auth_perm = getattr(request.state, "permission", None)

        # No menu operation permission identifier to verify
        if not path_auth_perm:
            return

        # Menu authentication whitelist
        if path_auth_perm in settings.RBAC_ROLE_MENU_EXCLUDE:
            return

        # Assigned menu permission verification
        allow_perms = []
        for role in user_roles:
            for menu in role.menus:
                if menu.perms and menu.status == StatusType.enable:
                    allow_perms.extend(menu.perms.split(","))
        if path_auth_perm not in allow_perms:
            raise AuthorizationError
    else:
        try:
            casbin_rbac = import_module_cached("plugin.casbin.utils.rbac")
            casbin_verify = getattr(casbin_rbac, "casbin_verify")
        except (ImportError, AttributeError) as e:
            log.error(
                f"Attempting to perform RBAC permission verification through casbin, but this plugin does not exist: {e}"
            )
            raise errors.ServerError(
                msg="Permission verification failed, please contact system administrator"
            )

        await casbin_verify(request)


# RBAC authorization dependency injection
DependsRBAC = Depends(rbac_verify)
