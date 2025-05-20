#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import zoneinfo

from datetime import datetime
from datetime import timezone as datetime_timezone

from core.conf import settings


class TimeZone:
    def __init__(self, tz: str = settings.DATETIME_TIMEZONE) -> None:
        """
        Initialize timezone converter

        :param tz: Timezone name, default is settings.DATETIME_TIMEZONE
        :return:
        """
        self.tz_info = zoneinfo.ZoneInfo(tz)

    def now(self) -> datetime:
        """Get current timezone time"""
        return datetime.now(self.tz_info)

    def f_datetime(self, dt: datetime) -> datetime:
        """
        Convert datetime object to current timezone time

        :param dt: The datetime object to be converted
        :return:
        """
        return dt.astimezone(self.tz_info)

    def f_str(self, date_str: str, format_str: str = settings.DATETIME_FORMAT) -> datetime:
        """
        Convert time string to datetime object in current timezone

        :param date_str: Time string
        :param format_str: Time format string, default is settings.DATETIME_FORMAT
        :return:
        """
        return datetime.strptime(date_str, format_str).replace(tzinfo=self.tz_info)

    @staticmethod
    def t_str(dt: datetime, format_str: str = settings.DATETIME_FORMAT) -> str:
        """
        Convert datetime object to time string with specified format

        :param dt: datetime object
        :param format_str: Time format string, default is settings.DATETIME_FORMAT
        :return:
        """
        return dt.strftime(format_str)

    @staticmethod
    def f_utc(dt: datetime) -> datetime:
        """
        Convert datetime object to UTC (GMT) timezone time

        :param dt: The datetime object to be converted
        :return:
        """
        return dt.astimezone(datetime_timezone.utc)


timezone: TimeZone = TimeZone()
