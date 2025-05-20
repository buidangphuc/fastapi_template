#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import VARBINARY, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import BYTEA, INTEGER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.admin.model.m2m import sys_user_role
from common.model import Base, id_key
from utils.string import uuid4_str
from utils.timezone import timezone

if TYPE_CHECKING:
    from app.admin.model import Dept, Role, UserSocial


class User(Base):
    """User model."""

    __tablename__ = 'sys_user'

    id: Mapped[id_key] = mapped_column(init=False)
    uuid: Mapped[str] = mapped_column(String(50), init=False, default_factory=uuid4_str, unique=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment='username')
    nickname: Mapped[str] = mapped_column(String(20), unique=True, comment='nickname')
    password: Mapped[str | None] = mapped_column(String(255), comment='password')
    salt: Mapped[bytes | None] = mapped_column(VARBINARY(255).with_variant(BYTEA(255), 'postgresql'), comment='password salt')
    email: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment='user email')
    is_superuser: Mapped[bool] = mapped_column(
        Boolean().with_variant(INTEGER, 'postgresql'), default=False, comment='Super user (0: no, 1: yes)')
    is_staff: Mapped[bool] = mapped_column(
        Boolean().with_variant(INTEGER, 'postgresql'), default=False, comment='Staff (0: no, 1: yes)')
    status: Mapped[int] = mapped_column(default=1, index=True, comment='User status (0: disabled, 1: normal)')
    is_multi_login: Mapped[bool] = mapped_column(
        Boolean().with_variant(INTEGER, 'postgresql'), default=False, comment='Allow multiple logins (0: no, 1: yes)')
    avatar: Mapped[str | None] = mapped_column(String(255), default=None, comment='user avatar')
    phone: Mapped[str | None] = mapped_column(String(11), default=None, comment='user phone')
    join_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, default_factory=timezone.now, comment='user join time')
    last_login_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), init=False, onupdate=timezone.now, comment='user last login time')
    # One-to-many department users
    dept_id: Mapped[int | None] = mapped_column(
        ForeignKey('sys_dept.id', ondelete='SET NULL'), default=None, comment='department ID'
    )
    dept: Mapped[Dept | None] = relationship(init=False, back_populates='users')

    # One-to-many user social information
    socials: Mapped[list[UserSocial]] = relationship(init=False, back_populates='user')

    # User roles many-to-many
    roles: Mapped[list[Role]] = relationship(init=False, secondary=sys_user_role, back_populates='users')
