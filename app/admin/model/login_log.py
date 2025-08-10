#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column

from common.model import DataClassBase, id_key
from utils.timezone import timezone


class LoginLog(DataClassBase):
    """Login log model."""

    __tablename__ = "sys_login_log"

    id: Mapped[id_key] = mapped_column(init=False)
    user_uuid: Mapped[str] = mapped_column(String(50), comment="user uuid")
    username: Mapped[str] = mapped_column(String(20), comment="username")
    status: Mapped[int] = mapped_column(
        insert_default=0, comment="Login status (0: success, 1: failure)"
    )
    ip: Mapped[str] = mapped_column(String(50), comment="Login IP")
    country: Mapped[str | None] = mapped_column(String(50), comment="country")
    region: Mapped[str | None] = mapped_column(String(50), comment="region")
    city: Mapped[str | None] = mapped_column(String(50), comment="city")
    user_agent: Mapped[str] = mapped_column(String(255), comment="user agent")
    os: Mapped[str | None] = mapped_column(String(50), comment="os")
    browser: Mapped[str | None] = mapped_column(String(50), comment="browser")
    device: Mapped[str | None] = mapped_column(String(50), comment="device")
    msg: Mapped[str] = mapped_column(
        LONGTEXT().with_variant(TEXT, "postgresql"), comment="login message"
    )
    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="login time"
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default_factory=timezone.now,
        comment="created time",
    )
