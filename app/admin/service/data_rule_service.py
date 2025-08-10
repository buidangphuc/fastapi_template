#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select

from app.admin.crud.crud_data_rule import data_rule_dao
from app.admin.crud.crud_role import role_dao
from app.admin.model import DataRule
from app.admin.schema.data_rule import CreateDataRuleParam, UpdateDataRuleParam
from common.exception import errors
from core.conf import settings
from database.db import AsyncSessionLocal
from database.redis import redis_client
from utils.import_parse import dynamic_import_data_model


class DataRuleService:
    """Data Rule Service Class"""

    @staticmethod
    async def get(*, pk: int) -> DataRule:
        """
        Get data rule details

        :param pk: Rule ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            data_rule = await data_rule_dao.get(db, pk)
            if not data_rule:
                raise errors.NotFoundError(msg="Data rule does not exist")
            return data_rule

    @staticmethod
    async def get_role_rules(*, pk: int) -> list[int]:
        """
        Get data rule list for a role

        :param pk: Role ID
        :return:
        """
        async with AsyncSessionLocal() as db:
            role = await role_dao.get_with_relation(db, pk)
            if not role:
                raise errors.NotFoundError(msg="Role does not exist")
            rule_ids = [rule.id for rule in role.rules]
            return rule_ids

    @staticmethod
    async def get_models() -> list[str]:
        """Get all models available for data rules"""
        return list(settings.DATA_PERMISSION_MODELS.keys())

    @staticmethod
    async def get_columns(model: str) -> list[str]:
        """
        Get field list for data rule available models

        :param model: Model name
        :return:
        """
        if model not in settings.DATA_PERMISSION_MODELS:
            raise errors.NotFoundError(msg="Data rule available model does not exist")
        model_ins = dynamic_import_data_model(settings.DATA_PERMISSION_MODELS[model])
        model_columns = [
            key
            for key in model_ins.__table__.columns.keys()
            if key not in settings.DATA_PERMISSION_COLUMN_EXCLUDE
        ]
        return model_columns

    @staticmethod
    async def get_select(*, name: str | None) -> Select:
        """
        Get data rule list query conditions

        :param name: Rule name
        :return:
        """
        return await data_rule_dao.get_list(name=name)

    @staticmethod
    async def get_all() -> Sequence[DataRule]:
        """Get all data rules"""
        async with AsyncSessionLocal() as db:
            data_rules = await data_rule_dao.get_all(db)
            return data_rules

    @staticmethod
    async def create(*, obj: CreateDataRuleParam) -> None:
        """
        Create data rule

        :param obj: Rule creation parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            data_rule = await data_rule_dao.get_by_name(db, obj.name)
            if data_rule:
                raise errors.ForbiddenError(msg="Data rule already exists")
            await data_rule_dao.create(db, obj)

    @staticmethod
    async def update(*, pk: int, obj: UpdateDataRuleParam) -> int:
        """
        Update data rule

        :param pk: Rule ID
        :param obj: Rule update parameters
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            data_rule = await data_rule_dao.get(db, pk)
            if not data_rule:
                raise errors.NotFoundError(msg="Data rule does not exist")
            count = await data_rule_dao.update(db, pk, obj)
            for role in await data_rule.awaitable_attrs.roles:
                for user in await role.awaitable_attrs.users:
                    await redis_client.delete(
                        f"{settings.JWT_USER_REDIS_PREFIX}:{user.id}"
                    )
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        """
        Delete data rule

        :param pk: Rule ID list
        :return:
        """
        async with AsyncSessionLocal.begin() as db:
            count = await data_rule_dao.delete(db, pk)
            for _pk in pk:
                data_rule = await data_rule_dao.get(db, _pk)
                if data_rule:
                    for role in await data_rule.awaitable_attrs.roles:
                        for user in await role.awaitable_attrs.users:
                            await redis_client.delete(
                                f"{settings.JWT_USER_REDIS_PREFIX}:{user.id}"
                            )
            return count


data_rule_service: DataRuleService = DataRuleService()
