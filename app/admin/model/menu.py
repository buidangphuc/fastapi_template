#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.admin.model.m2m import sys_role_menu
from common.model import Base, id_key

if TYPE_CHECKING:
    from app.admin.model import Role


class Menu(Base):
    """Menu model."""

    __tablename__ = "sys_menu"

    id: Mapped[id_key] = mapped_column(init=False)
    title: Mapped[str] = mapped_column(String(50), comment="menu title")
    name: Mapped[str] = mapped_column(String(50), comment="menu name")
    path: Mapped[str] = mapped_column(String(200), comment="menu path")
    sort: Mapped[int] = mapped_column(default=0, comment="sort order")
    icon: Mapped[str | None] = mapped_column(
        String(100), default=None, comment="menu icon"
    )
    type: Mapped[int] = mapped_column(
        default=0, comment="Menu type (0 directory 1 menu 2 button)"
    )
    component: Mapped[str | None] = mapped_column(
        String(255), default=None, comment="menu component"
    )
    perms: Mapped[str | None] = mapped_column(
        String(100), default=None, comment="menu permissions"
    )
    status: Mapped[int] = mapped_column(
        default=1, comment="Menu status (0 disabled 1 normal)"
    )
    display: Mapped[int] = mapped_column(
        default=1, comment="Menu display (0 hidden 1 shown)"
    )
    cache: Mapped[int] = mapped_column(
        default=1, comment="Cache menu (0 not cached 1 cached)"
    )
    link: Mapped[str | None] = mapped_column(
        LONGTEXT().with_variant(TEXT, "postgresql"), default=None, comment="menu link"
    )
    remark: Mapped[str | None] = mapped_column(
        LONGTEXT().with_variant(TEXT, "postgresql"), default=None, comment="menu remark"
    )

    # Parent Menu One-to-Many
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("sys_menu.id", ondelete="SET NULL"),
        default=None,
        index=True,
        comment="parent menu ID",
    )
    parent: Mapped[Optional["Menu"]] = relationship(
        init=False, back_populates="children", remote_side=[id]
    )
    children: Mapped[Optional[list["Menu"]]] = relationship(
        init=False, back_populates="parent"
    )

    # One-to-many menu roles
    roles: Mapped[list[Role]] = relationship(
        init=False, secondary=sys_role_menu, back_populates="menus"
    )
