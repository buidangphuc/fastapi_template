#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.admin.model.m2m import sys_role_data_rule, sys_role_menu, sys_user_role
from common.model import Base, id_key

if TYPE_CHECKING:
    from app.admin.model import DataRule, Menu, User


class Role(Base):
    """Role model."""

    __tablename__ = "sys_role"

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(20), unique=True, comment="role name")
    status: Mapped[int] = mapped_column(
        default=1, comment="role status (0 disabled 1 normal)"
    )
    remark: Mapped[str | None] = mapped_column(
        LONGTEXT().with_variant(TEXT, "postgresql"), default=None, comment="role remark"
    )

    # One-to-many role users
    users: Mapped[list[User]] = relationship(
        init=False, secondary=sys_user_role, back_populates="roles"
    )

    # One-to-many role menus
    menus: Mapped[list[Menu]] = relationship(
        init=False, secondary=sys_role_menu, back_populates="roles"
    )

    # One-to-many role data rules
    rules: Mapped[list[DataRule]] = relationship(
        init=False, secondary=sys_role_data_rule, back_populates="roles"
    )
