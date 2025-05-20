#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query

from app.admin.schema.role import (
    CreateRoleParam,
    GetRoleDetail,
    GetRoleWithRelationDetail,
    UpdateRoleMenuParam,
    UpdateRoleParam,
    UpdateRoleRuleParam,
)
from app.admin.service.data_rule_service import data_rule_service
from app.admin.service.menu_service import menu_service
from app.admin.service.role_service import role_service
from common.pagination import DependsPagination, PageData, paging_data
from common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from common.security.jwt import DependsJwtAuth
from common.security.permission import RequestPermission
from common.security.rbac import DependsRBAC
from database.db import CurrentSession

router = APIRouter()


@router.get('/all', summary='Get all roles', dependencies=[DependsJwtAuth])
async def get_all_roles() -> ResponseSchemaModel[list[GetRoleDetail]]:
    data = await role_service.get_all()
    return response_base.success(data=data)


@router.get('/{pk}/all', summary='Get all roles of a user', dependencies=[DependsJwtAuth])
async def get_user_all_roles(
    pk: Annotated[int, Path(description='user ID')],
) -> ResponseSchemaModel[list[GetRoleDetail]]:
    data = await role_service.get_by_user(pk=pk)
    return response_base.success(data=data)


@router.get('/{pk}/menus', summary='Get all character menus', dependencies=[DependsJwtAuth])
async def get_role_all_menus(
    pk: Annotated[int, Path(description='role ID')],
) -> ResponseSchemaModel[list[dict[str, Any]]]:
    menu = await menu_service.get_role_menu_tree(pk=pk)
    return response_base.success(data=menu)


@router.get('/{pk}/rules', summary='Get all data rules of the role', dependencies=[DependsJwtAuth])
async def get_role_all_rules(pk: Annotated[int, Path(description='role ID')]) -> ResponseSchemaModel[list[int]]:
    rule = await data_rule_service.get_role_rules(pk=pk)
    return response_base.success(data=rule)


@router.get('/{pk}', summary='Get role details', dependencies=[DependsJwtAuth])
async def get_role(
    pk: Annotated[int, Path(description='role ID')],
) -> ResponseSchemaModel[GetRoleWithRelationDetail]:
    data = await role_service.get(pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='Get all roles by page',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_roles(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='role name')] = None,
    status: Annotated[int | None, Query(description='status')] = None,
) -> ResponseSchemaModel[PageData[GetRoleDetail]]:
    role_select = await role_service.get_select(name=name, status=status)
    page_data = await paging_data(db, role_select)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='Create a new role',
    dependencies=[
        Depends(RequestPermission('sys:role:add')),
        DependsRBAC,
    ],
)
async def create_role(obj: CreateRoleParam) -> ResponseModel:
    await role_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='Update role',
    dependencies=[
        Depends(RequestPermission('sys:role:edit')),
        DependsRBAC,
    ],
)
async def update_role(pk: Annotated[int, Path(description='role ID')], obj: UpdateRoleParam) -> ResponseModel:
    count = await role_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put(
    '/{pk}/menu',
    summary='Update role menus',
    dependencies=[
        Depends(RequestPermission('sys:role:menu:edit')),
        DependsRBAC,
    ],
)
async def update_role_menus(
    pk: Annotated[int, Path(description='role ID')], menu_ids: UpdateRoleMenuParam
) -> ResponseModel:
    count = await role_service.update_role_menu(pk=pk, menu_ids=menu_ids)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put(
    '/{pk}/rule',
    summary='Update role data rules',
    dependencies=[
        Depends(RequestPermission('sys:role:rule:edit')),
        DependsRBAC,
    ],
)
async def update_role_rules(
    pk: Annotated[int, Path(description='role ID')], rule_ids: UpdateRoleRuleParam
) -> ResponseModel:
    count = await role_service.update_role_rule(pk=pk, rule_ids=rule_ids)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='Delete role in batch',
    dependencies=[
        Depends(RequestPermission('sys:role:del')),
        DependsRBAC,
    ],
)
async def delete_role(pk: Annotated[list[int], Query(description='role ID list')]) -> ResponseModel:
    count = await role_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
