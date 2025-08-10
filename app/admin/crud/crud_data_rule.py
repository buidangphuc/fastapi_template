#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Sequence

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload
from sqlalchemy_crud_plus import CRUDPlus

from app.admin.model import DataRule
from app.admin.schema.data_rule import CreateDataRuleParam, UpdateDataRuleParam


class CRUDDataRule(CRUDPlus[DataRule]):
    """CRUD for DataRule model."""

    async def get(self, db: AsyncSession, pk: int) -> DataRule | None:
        """
        Get a data rule by primary key.

        :param db: db session
        :param pk: rule ID
        :return:
        """
        return await self.select_model(db, pk)

    async def get_list(self, name: str | None) -> Select:
        """
        Get a list of data rules.

        :param name: Rule name
        :return:
        """
        stmt = (
            select(self.model)
            .options(noload(self.model.roles))
            .order_by(desc(self.model.created_time))
        )

        filters = []
        if name is not None:
            filters.append(self.model.name.like(f"%{name}%"))

        if filters:
            stmt = stmt.where(and_(*filters))

        return stmt

    async def get_by_name(self, db: AsyncSession, name: str) -> DataRule | None:
        """
        Get a data rule by name.

        :param db: db session
        :param name: rule name
        :return:
        """
        return await self.select_model_by_column(db, name=name)

    async def get_all(self, db: AsyncSession) -> Sequence[DataRule]:
        """
        Get all data rules.

        :param db: db session
        :return:
        """
        return await self.select_models(db)

    async def create(self, db: AsyncSession, obj: CreateDataRuleParam) -> None:
        """
        Create a new data rule.

        :param db: db session
        :param obj: rule parameters
        :return:
        """
        await self.create_model(db, obj)

    async def update(self, db: AsyncSession, pk: int, obj: UpdateDataRuleParam) -> int:
        """
        Update an existing data rule.

        :param db: db session
        :param pk: rule ID
        :param obj: rule parameters
        :return:
        """
        return await self.update_model(db, pk, obj)

    async def delete(self, db: AsyncSession, pk: list[int]) -> int:
        """
        Delete data rules.

        :param db: db session
        :param pk: rule ID list
        :return:
        """
        return await self.delete_model_by_column(db, allow_multiple=True, id__in=pk)


data_rule_dao: CRUDDataRule = CRUDDataRule(DataRule)
