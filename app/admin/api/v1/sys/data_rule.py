#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.admin.schema.data_rule import CreateDataRuleParam, GetDataRuleDetail, UpdateDataRuleParam
from app.admin.service.data_rule_service import data_rule_service
from common.pagination import DependsPagination, PageData, paging_data
from common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from common.security.jwt import DependsJwtAuth
from common.security.permission import RequestPermission
from common.security.rbac import DependsRBAC
from database.db import CurrentSession

router = APIRouter()


@router.get('/models', summary='Get data rule available models', dependencies=[DependsJwtAuth])
async def get_data_rule_models() -> ResponseSchemaModel[list[str]]:
    models = await data_rule_service.get_models()
    return response_base.success(data=models)


@router.get('/model/{model}/columns', summary='Get the available model columns for data rules', dependencies=[DependsJwtAuth])
async def get_data_rule_model_columns(
    model: Annotated[str, Path(description='Model name')],
) -> ResponseSchemaModel[list[str]]:
    models = await data_rule_service.get_columns(model=model)
    return response_base.success(data=models)


@router.get('/all', summary='Get all data rules', dependencies=[DependsJwtAuth])
async def get_all_data_rules() -> ResponseSchemaModel[list[GetDataRuleDetail]]:
    data = await data_rule_service.get_all()
    return response_base.success(data=data)


@router.get('/{pk}', summary='Get data rule details', dependencies=[DependsJwtAuth])
async def get_data_rule(
    pk: Annotated[int, Path(description='Data rules ID')],
) -> ResponseSchemaModel[GetDataRuleDetail]:
    data = await data_rule_service.get(pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='Get data rules pagination',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_pagination_data_rules(
    db: CurrentSession, name: Annotated[str | None, Query(description='Rule name')] = None
) -> ResponseSchemaModel[PageData[GetDataRuleDetail]]:
    data_rule_select = await data_rule_service.get_select(name=name)
    page_data = await paging_data(db, data_rule_select)
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='Create data rule',
    dependencies=[
        Depends(RequestPermission('data:rule:add')),
        DependsRBAC,
    ],
)
async def create_data_rule(obj: CreateDataRuleParam) -> ResponseModel:
    await data_rule_service.create(obj=obj)
    return response_base.success()


@router.put(
    '/{pk}',
    summary='Update data rule',
    dependencies=[
        Depends(RequestPermission('data:rule:edit')),
        DependsRBAC,
    ],
)
async def update_data_rule(
    pk: Annotated[int, Path(description='Data rule ID')], obj: UpdateDataRuleParam
) -> ResponseModel:
    count = await data_rule_service.update(pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='Batch delete data rules',
    dependencies=[
        Depends(RequestPermission('data:rule:del')),
        DependsRBAC,
    ],
)
async def delete_data_rule(pk: Annotated[list[int], Query(description='Data rule ID list')]) -> ResponseModel:
    count = await data_rule_service.delete(pk=pk)
    if count > 0:
        return response_base.success()
    return response_base.fail()
