#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import TYPE_CHECKING

from fastapi import Request
from sqlalchemy import ColumnElement, and_, or_

from common.enums import RoleDataRuleExpressionType, RoleDataRuleOperatorType
from common.exception import errors
from common.exception.errors import ServerError
from core.conf import settings
from utils.import_parse import dynamic_import_data_model

if TYPE_CHECKING:
    from app.admin.schema.data_rule import GetDataRuleDetail


class RequestPermission:
    """
    Request permission validator, used for role menu RBAC permission control

    Note:
        When using this request permission, you need to set `Depends(RequestPermission('xxx'))` before `DependsRBAC`,
        because the current version of FastAPI's interface dependency injection executes in sequential order,
        meaning the RBAC identifier will be set before verification
    """

    def __init__(self, value: str) -> None:
        """
        Initialize request permission validator

        :param value: Permission identifier
        :return:
        """
        self.value = value

    async def __call__(self, request: Request) -> None:
        """
        Verify request permission

        :param request: FastAPI request object
        :return:
        """
        if settings.RBAC_ROLE_MENU_MODE:
            if not isinstance(self.value, str):
                raise ServerError
            # Attach permission identifier to request state
            request.state.permission = self.value


def filter_data_permission(request: Request) -> ColumnElement[bool]:
    """
    Filter data permissions, control user visible data scope

    Use cases:
        - After user logs in to the frontend, control what data they can see
        - Filter data access permissions based on user roles and rules

    :param request: FastAPI request object
    :return:
    """
    # Get user roles and rules
    data_rules = []
    for role in request.user.roles:
        data_rules.extend(role.rules)
    user_data_rules: list[GetDataRuleDetail] = list(dict.fromkeys(data_rules))

    # Super admins and users without rules are not filtered
    if request.user.is_superuser or not user_data_rules:
        return or_(1 == 1)

    where_and_list = []
    where_or_list = []

    for rule in user_data_rules:
        # Verify rule model
        rule_model = rule.model
        if rule_model not in settings.DATA_PERMISSION_MODELS:
            raise errors.NotFoundError(msg='Data rule model does not exist')
        model_ins = dynamic_import_data_model(settings.DATA_PERMISSION_MODELS[rule_model])

        # Verify rule column
        model_columns = [
            key for key in model_ins.__table__.columns.keys() if key not in settings.DATA_PERMISSION_COLUMN_EXCLUDE
        ]
        column = rule.column
        if column not in model_columns:
            raise errors.NotFoundError(msg='Data rule model column does not exist')

        # Build filter conditions
        column_obj = getattr(model_ins, column)
        rule_expression = rule.expression
        condition = None
        if rule_expression == RoleDataRuleExpressionType.eq:
            condition = column_obj == rule.value
        elif rule_expression == RoleDataRuleExpressionType.ne:
            condition = column_obj != rule.value
        elif rule_expression == RoleDataRuleExpressionType.gt:
            condition = column_obj > rule.value
        elif rule_expression == RoleDataRuleExpressionType.ge:
            condition = column_obj >= rule.value
        elif rule_expression == RoleDataRuleExpressionType.lt:
            condition = column_obj < rule.value
        elif rule_expression == RoleDataRuleExpressionType.le:
            condition = column_obj <= rule.value
        elif rule_expression == RoleDataRuleExpressionType.in_:
            values = rule.value.split(',') if isinstance(rule.value, str) else rule.value
            condition = column_obj.in_(values)
        elif rule.expression == RoleDataRuleExpressionType.not_in:
            values = rule.value.split(',') if isinstance(rule.value, str) else rule.value
            condition = ~column_obj.in_(values)

        # Add to corresponding list based on operator
        if condition is not None:
            if rule.operator == RoleDataRuleOperatorType.AND:
                where_and_list.append(condition)
            elif rule.operator == RoleDataRuleOperatorType.OR:
                where_or_list.append(condition)

    # Combine all conditions
    where_list = []
    if where_and_list:
        where_list.append(and_(*where_and_list))
    if where_or_list:
        where_list.append(or_(*where_or_list))

    return or_(*where_list) if where_list else or_(1 == 1)
