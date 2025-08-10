#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.mysql import JSON, LONGTEXT
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Mapped, mapped_column

from common.model import DataClassBase, id_key
from utils.timezone import timezone


class OperaLog(DataClassBase):
    """Operation log model."""

    __tablename__ = "sys_opera_log"

    id: Mapped[id_key] = mapped_column(init=False)
    trace_id: Mapped[str] = mapped_column(String(32), comment="trace ID")
    username: Mapped[str | None] = mapped_column(String(20), comment="username")
    method: Mapped[str] = mapped_column(String(20), comment="request method")
    title: Mapped[str] = mapped_column(String(255), comment="operation title")
    path: Mapped[str] = mapped_column(String(500), comment="request path")
    ip: Mapped[str] = mapped_column(String(50), comment="request IP")
    country: Mapped[str | None] = mapped_column(String(50), comment="country")
    region: Mapped[str | None] = mapped_column(String(50), comment="region")
    city: Mapped[str | None] = mapped_column(String(50), comment="city")
    user_agent: Mapped[str] = mapped_column(String(255), comment="user agent")
    os: Mapped[str | None] = mapped_column(String(50), comment="os")
    browser: Mapped[str | None] = mapped_column(String(50), comment="browser")
    device: Mapped[str | None] = mapped_column(String(50), comment="device")
    args: Mapped[str | None] = mapped_column(JSON(), comment="request args")
    status: Mapped[int] = mapped_column(
        comment="operation status (0: success, 1: failure)"
    )
    code: Mapped[str] = mapped_column(
        String(20), insert_default="200", comment="response code"
    )
    msg: Mapped[str | None] = mapped_column(
        LONGTEXT().with_variant(TEXT, "postgresql"), comment="message"
    )
    cost_time: Mapped[float] = mapped_column(
        insert_default=0.0, comment="cost time (ms)"
    )
    opera_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="operation time"
    )
    created_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        default_factory=timezone.now,
        comment="created time",
    )
