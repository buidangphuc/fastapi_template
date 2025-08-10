#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from database.redis import redis_client
from utils.server_info import server_info


class RedisInfo:
    @staticmethod
    async def get_info() -> dict[str, str]:
        """Get Redis server information"""

        # Get original information
        info = await redis_client.info()

        # Format information
        fmt_info: dict[str, str] = {}
        for key, value in info.items():
            if isinstance(value, dict):
                # Format dictionary to string
                fmt_info[key] = ",".join(f"{k}={v}" for k, v in value.items())
            else:
                fmt_info[key] = str(value)

        # Add database size information
        db_size = await redis_client.dbsize()
        fmt_info["keys_num"] = str(db_size)

        # Format runtime
        uptime = int(fmt_info.get("uptime_in_seconds", "0"))
        fmt_info["uptime_in_seconds"] = server_info.fmt_seconds(uptime)

        return fmt_info

    @staticmethod
    async def get_stats() -> list[dict[str, str]]:
        """Get Redis command statistics"""

        # Get command statistics
        command_stats = await redis_client.info("commandstats")

        # Format statistics
        stats_list: list[dict[str, str]] = []
        for key, value in command_stats.items():
            if not isinstance(value, dict):
                continue

            command_name = key.split("_")[-1]
            call_count = str(value.get("calls", "0"))
            stats_list.append({"name": command_name, "value": call_count})

        return stats_list


redis_info: RedisInfo = RedisInfo()
