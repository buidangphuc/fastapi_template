#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import INTEGER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.model import Base, id_key

if TYPE_CHECKING:
    from app.admin.model import User


class Dept(Base):
    """Department model."""

    __tablename__ = 'sys_dept'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(String(50), comment='department name')
    sort: Mapped[int] = mapped_column(default=0, comment='sort order')
    leader: Mapped[str | None] = mapped_column(String(20), default=None, comment='leader name')
    phone: Mapped[str | None] = mapped_column(String(11), default=None, comment='leader phone')
    email: Mapped[str | None] = mapped_column(String(50), default=None, comment='leader email')
    status: Mapped[int] = mapped_column(default=1, comment='Department status (0 disabled 1 normal)')
    del_flag: Mapped[bool] = mapped_column(
        Boolean().with_variant(INTEGER, 'postgresql'), default=False, comment='Delete flag (0 to delete, 1 to exist)'
    )

    # Parent Department One-to-Many
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_dept.id', ondelete='SET NULL'), default=None, index=True, comment='parent department ID'
    )
    parent: Mapped[Optional['Dept']] = relationship(init=False, back_populates='children', remote_side=[id])
    children: Mapped[Optional[list['Dept']]] = relationship(init=False, back_populates='parent')

    # One-to-many department users
    users: Mapped[list[User]] = relationship(init=False, back_populates='dept')
