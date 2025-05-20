#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.admin.model.m2m import sys_role_data_rule
from common.model import Base, id_key

if TYPE_CHECKING:
    from app.admin.model import Role


class DataRule(Base):
    """Data rule model."""

    __tablename__ = 'sys_data_rule'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, comment='rule name')
    model: Mapped[str] = mapped_column(String(50), comment='SQLA model')
    column: Mapped[str] = mapped_column(String(20), comment='rule column')
    operator: Mapped[int] = mapped_column(comment='Operator (0: and, 1: or)')
    expression: Mapped[int] = mapped_column(
        comment='Expression (0:==、1：!=、2：>、3：>=、4：<、5：<=、6：in、7：not_in）'
    )
    value: Mapped[str] = mapped_column(String(255), comment='rule value')

    # Relationships
    roles: Mapped[list[Role]] = relationship(init=False, secondary=sys_role_data_rule, back_populates='rules')
