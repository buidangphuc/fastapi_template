from __future__ import annotations

from datetime import UTC, datetime

from pymongo import ReturnDocument

from app.modules.platform.mongo.gateway import MongoGateway
from app.modules.platform.quota.models import (
    QuotaReservation,
    QuotaReservationStatus,
    QuotaUsage,
    QuotaUsageQuery,
    ReserveQuota,
)

DEFAULT_QUOTA_COUNTER_COLLECTION = "quota_counters"
DEFAULT_QUOTA_RESERVATION_COLLECTION = "quota_reservations"


class MongoQuotaStore:
    def __init__(
        self,
        gateway: MongoGateway,
        *,
        counter_collection: str = DEFAULT_QUOTA_COUNTER_COLLECTION,
        reservation_collection: str = DEFAULT_QUOTA_RESERVATION_COLLECTION,
    ) -> None:
        self._counters = gateway.collection(counter_collection)
        self._reservations = gateway.collection(reservation_collection)

    async def reserve(self, command: ReserveQuota) -> QuotaReservation | None:
        await self._migrate_active_counters(command)
        existing = await self._find_idempotent_reservation(command)
        if existing is not None:
            return await self._to_reservation(existing)

        counter_key = _counter_key(command)
        await self._counters.update_one(
            counter_key,
            {
                "$setOnInsert": {
                    **counter_key,
                    "used": 0,
                },
                "$set": {
                    "limit": command.limit,
                    "reset_at": command.reset_at,
                },
            },
            upsert=True,
        )
        counter = await self._counters.find_one_and_update(
            {
                **counter_key,
                "$expr": {
                    "$lte": [
                        {"$add": ["$used", command.cost]},
                        command.limit,
                    ]
                },
            },
            {
                "$inc": {"used": command.cost},
                "$set": {
                    "limit": command.limit,
                    "reset_at": command.reset_at,
                },
            },
            return_document=ReturnDocument.AFTER,
        )
        if counter is None:
            return None

        reservation_doc = {
            "_id": command.reservation_id,
            "subject_id": command.subject_id,
            "resource": command.resource,
            "window_key": command.window_key,
            "cost": command.cost,
            "status": QuotaReservationStatus.RESERVED.value,
            "idempotency_key": command.idempotency_key,
            "reset_at": command.reset_at,
        }
        await self._reservations.insert_one(reservation_doc)
        return _reservation_from_doc(reservation_doc, _usage_from_counter(counter))

    async def finalize(self, reservation_id: str) -> QuotaUsage:
        reservation = await self._require_reservation(reservation_id)
        status = QuotaReservationStatus(reservation["status"])
        if status == QuotaReservationStatus.REFUNDED:
            raise ValueError("refunded reservation cannot be finalized")
        if status == QuotaReservationStatus.RESERVED:
            await self._reservations.update_one(
                {"_id": reservation_id},
                {"$set": {"status": QuotaReservationStatus.FINALIZED.value}},
            )
        return await self._usage_for_reservation(reservation)

    async def refund(self, reservation_id: str) -> QuotaUsage:
        reservation = await self._require_reservation(reservation_id)
        status = QuotaReservationStatus(reservation["status"])
        if status == QuotaReservationStatus.FINALIZED:
            raise ValueError("finalized reservation cannot be refunded")
        if status == QuotaReservationStatus.REFUNDED:
            return await self._usage_for_reservation(reservation)

        counter = await self._counters.find_one_and_update(
            {
                "subject_id": reservation["subject_id"],
                "resource": reservation["resource"],
                "window_key": reservation["window_key"],
            },
            {
                "$inc": {"used": -reservation["cost"]},
            },
            return_document=ReturnDocument.AFTER,
        )
        await self._reservations.update_one(
            {"_id": reservation_id},
            {"$set": {"status": QuotaReservationStatus.REFUNDED.value}},
        )
        if counter is None:
            raise KeyError(reservation_id)
        return _usage_from_counter(counter)

    async def get_usage(self, query: QuotaUsageQuery) -> QuotaUsage:
        await self._migrate_active_counters(query)
        counter = await self._counters.find_one_and_update(
            {
                "subject_id": query.subject_id,
                "resource": query.resource,
                "window_key": query.window_key,
            },
            {
                "$set": {
                    "limit": query.limit,
                    "reset_at": query.reset_at,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if counter is None:
            return QuotaUsage(
                subject_id=query.subject_id,
                resource=query.resource,
                window_key=query.window_key,
                used=0,
                limit=query.limit,
                remaining=query.limit,
                reset_at=query.reset_at,
            )
        return _usage_from_counter(counter)

    async def reset_usage(self, query: QuotaUsageQuery) -> QuotaUsage:
        key = {
            "subject_id": query.subject_id,
            "resource": query.resource,
        }
        await self._reservations.delete_many(key)
        await self._counters.delete_many(key)
        return _usage_from_query(query)

    async def reset_resource(self, resource: str) -> None:
        key = {"resource": resource}
        await self._reservations.delete_many(key)
        await self._counters.delete_many(key)

    async def close(self) -> None:
        return None

    async def _find_idempotent_reservation(self, command: ReserveQuota) -> dict | None:
        if command.idempotency_key is None:
            return None
        return await self._reservations.find_one(
            {
                "subject_id": command.subject_id,
                "resource": command.resource,
                "window_key": command.window_key,
                "idempotency_key": command.idempotency_key,
            }
        )

    async def _migrate_active_counters(
        self,
        command: ReserveQuota | QuotaUsageQuery,
    ) -> None:
        now = datetime.now(UTC)
        cursor = self._counters.find(
            {
                "subject_id": command.subject_id,
                "resource": command.resource,
            }
        )
        target: dict | None = None
        stale: list[dict] = []
        async for counter in cursor:
            if counter["window_key"] == command.window_key:
                target = counter
            elif counter["reset_at"] > now:
                stale.append(counter)

        if not stale:
            if target is not None:
                await self._counters.update_one(
                    {
                        "subject_id": command.subject_id,
                        "resource": command.resource,
                        "window_key": command.window_key,
                    },
                    {
                        "$set": {
                            "limit": command.limit,
                            "reset_at": command.reset_at,
                        }
                    },
                )
            return

        used = int(target["used"]) if target is not None else 0
        used += sum(int(counter["used"]) for counter in stale)
        counter_key = {
            "subject_id": command.subject_id,
            "resource": command.resource,
            "window_key": command.window_key,
        }
        await self._counters.update_one(
            counter_key,
            {
                "$setOnInsert": counter_key,
                "$set": {
                    "used": used,
                    "limit": command.limit,
                    "reset_at": command.reset_at,
                },
            },
            upsert=True,
        )
        for counter in stale:
            stale_key = {
                "subject_id": command.subject_id,
                "resource": command.resource,
                "window_key": counter["window_key"],
            }
            await self._reservations.update_many(
                stale_key,
                {
                    "$set": {
                        "window_key": command.window_key,
                        "reset_at": command.reset_at,
                    }
                },
            )
            await self._counters.delete_many(stale_key)

    async def _require_reservation(self, reservation_id: str) -> dict:
        reservation = await self._reservations.find_one({"_id": reservation_id})
        if reservation is None:
            raise KeyError(reservation_id)
        return reservation

    async def _usage_for_reservation(self, reservation: dict) -> QuotaUsage:
        counter = await self._counters.find_one(
            {
                "subject_id": reservation["subject_id"],
                "resource": reservation["resource"],
                "window_key": reservation["window_key"],
            }
        )
        if counter is None:
            raise KeyError(reservation["_id"])
        return _usage_from_counter(counter)

    async def _to_reservation(self, reservation: dict) -> QuotaReservation:
        return _reservation_from_doc(
            reservation, await self._usage_for_reservation(reservation)
        )


def _counter_key(command: ReserveQuota) -> dict:
    return {
        "subject_id": command.subject_id,
        "resource": command.resource,
        "window_key": command.window_key,
    }


def _usage_from_counter(counter: dict) -> QuotaUsage:
    limit = int(counter["limit"])
    used = int(counter["used"])
    return QuotaUsage(
        subject_id=counter["subject_id"],
        resource=counter["resource"],
        window_key=counter["window_key"],
        used=used,
        limit=limit,
        remaining=max(limit - used, 0),
        reset_at=counter["reset_at"],
    )


def _usage_from_query(query: QuotaUsageQuery) -> QuotaUsage:
    return QuotaUsage(
        subject_id=query.subject_id,
        resource=query.resource,
        window_key=query.window_key,
        used=0,
        limit=query.limit,
        remaining=query.limit,
        reset_at=query.reset_at,
    )


def _reservation_from_doc(doc: dict, usage: QuotaUsage) -> QuotaReservation:
    return QuotaReservation(
        id=doc["_id"],
        subject_id=doc["subject_id"],
        resource=doc["resource"],
        window_key=doc["window_key"],
        cost=doc["cost"],
        status=QuotaReservationStatus(doc["status"]),
        usage=usage,
        idempotency_key=doc.get("idempotency_key"),
    )
