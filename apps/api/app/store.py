"""Persistence boundary for webhook, bounty, and review workflow state."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DuplicateDelivery(Exception):
    pass


class DuplicateBounty(Exception):
    pass


class Store:
    async def ensure_indexes(self) -> None: ...
    async def record_delivery(self, delivery_id: str, event_type: str, payload_hash: str) -> bool: ...
    async def create_bounty(self, bounty: dict[str, Any]) -> dict[str, Any]: ...
    async def list_bounties(self) -> list[dict[str, Any]]: ...
    async def get_bounty(self, contract_bounty_id: str) -> dict[str, Any] | None: ...
    async def update_bounty(self, contract_bounty_id: str, values: dict[str, Any]) -> None: ...
    async def find_bounty(self, repository: str) -> dict[str, Any] | None: ...
    async def create_review(self, review: dict[str, Any]) -> tuple[dict[str, Any], bool]: ...
    async def update_review(self, review_id: str, values: dict[str, Any]) -> None: ...
    async def get_review(self, review_id: str) -> dict[str, Any] | None: ...
    async def save_agent_results(
        self,
        review_id: str,
        results: list[dict[str, Any]],
    ) -> None: ...
    async def save_evidence(self, review_id: str, evidence_bytes: bytes, evidence_hash: str, evidence_cid: str) -> None: ...
    async def get_evidence(self, review_id: str) -> dict[str, Any] | None: ...


class MemoryStore(Store):
    def __init__(self) -> None:
        self.deliveries: dict[str, dict[str, Any]] = {}
        self.bounties: dict[str, dict[str, Any]] = {}
        self.reviews: dict[str, dict[str, Any]] = {}
        self.agent_results: dict[str, list[dict[str, Any]]] = {}
        self.evidence: dict[str, dict[str, Any]] = {}
        self.dedupe_keys: set[str] = set()

    async def ensure_indexes(self) -> None:
        return None

    async def record_delivery(self, delivery_id: str, event_type: str, payload_hash: str) -> bool:
        if delivery_id in self.deliveries:
            return False
        self.deliveries[delivery_id] = {"delivery_id": delivery_id, "event_type": event_type, "payload_hash": payload_hash, "status": "received", "created_at": utcnow()}
        return True

    async def create_bounty(self, bounty: dict[str, Any]) -> dict[str, Any]:
        if any(item["contract_bounty_id"] == bounty["contract_bounty_id"] for item in self.bounties.values()):
            raise DuplicateBounty(bounty["contract_bounty_id"])
        record = {**bounty, "id": str(uuid4()), "created_at": utcnow(), "updated_at": utcnow()}
        self.bounties[record["id"]] = record
        return deepcopy(record)

    async def list_bounties(self) -> list[dict[str, Any]]:
        return [deepcopy(bounty) for bounty in sorted(self.bounties.values(), key=lambda item: item["created_at"], reverse=True)]

    async def get_bounty(self, contract_bounty_id: str) -> dict[str, Any] | None:
        bounty = next((item for item in self.bounties.values() if item["contract_bounty_id"] == contract_bounty_id), None)
        return deepcopy(bounty) if bounty else None

    async def update_bounty(self, contract_bounty_id: str, values: dict[str, Any]) -> None:
        bounty = next((item for item in self.bounties.values() if item["contract_bounty_id"] == contract_bounty_id), None)
        if bounty is None:
            raise KeyError(contract_bounty_id)
        bounty.update(values | {"updated_at": utcnow()})

    async def find_bounty(self, repository: str) -> dict[str, Any] | None:
        for bounty in self.bounties.values():
            if bounty["repository"] == repository and bounty["status"] == "open":
                return deepcopy(bounty)
        return None

    async def create_review(self, review: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        if review["dedupe_key"] in self.dedupe_keys:
            existing = next(item for item in self.reviews.values() if item["dedupe_key"] == review["dedupe_key"])
            return deepcopy(existing), False
        record = {**review, "id": str(uuid4()), "created_at": utcnow(), "updated_at": utcnow()}
        self.dedupe_keys.add(record["dedupe_key"])
        self.reviews[record["id"]] = record
        return deepcopy(record), True

    async def update_review(self, review_id: str, values: dict[str, Any]) -> None:
        self.reviews[review_id].update(values | {"updated_at": utcnow()})

    async def get_review(self, review_id: str) -> dict[str, Any] | None:
        review = self.reviews.get(review_id)
        return deepcopy(review) if review else None
    async def save_agent_results(self, review_id: str, results: list[dict[str, Any]]) -> None:
        self.agent_results[review_id] = [{"review_id": review_id, **result, "created_at": utcnow()} for result in results]

    async def save_evidence(self, review_id: str, evidence_bytes: bytes, evidence_hash: str, evidence_cid: str) -> None:
        self.evidence[review_id] = {
            "review_id": review_id,
            "evidence_bytes": evidence_bytes,
            "evidence_hash": evidence_hash,
            "evidence_cid": evidence_cid,
            "created_at": utcnow(),
        }

    async def get_evidence(self, review_id: str) -> dict[str, Any] | None:
        evidence = self.evidence.get(review_id)
        return deepcopy(evidence) if evidence else None


class MongoStore(Store):
    def __init__(self, uri: str, database: str) -> None:
        from motor.motor_asyncio import AsyncIOMotorClient

        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[database]

    async def ensure_indexes(self) -> None:
        validators = {
            "bounties": ["id", "contract_bounty_id", "repository", "status", "created_at"],
            "reviews": ["id", "bounty_id", "repository", "pr_number", "commit_sha", "dedupe_key", "status", "created_at"],
            "evidence": ["review_id", "evidence_bytes", "evidence_hash", "evidence_cid", "created_at"],
            "agent_results": ["review_id", "agent", "score_bps", "created_at"],
            "disputes": ["bounty_id", "review_id", "status", "created_at"],
            "webhook_events": ["delivery_id", "event_type", "payload_hash", "status", "created_at"],
        }
        existing = await self.db.list_collection_names()
        for collection, required in validators.items():
            validator = {"$jsonSchema": {"bsonType": "object", "required": required}}
            if collection not in existing:
                await self.db.create_collection(collection, validator=validator)
            else:
                await self.db.command({"collMod": collection, "validator": validator, "validationLevel": "moderate"})
        await self.db.webhook_events.create_index("delivery_id", unique=True)
        await self.db.bounties.create_index("contract_bounty_id", unique=True)
        await self.db.reviews.create_index("dedupe_key", unique=True)
        await self.db.bounties.create_index([("repository", 1), ("status", 1)])
        await self.db.reviews.create_index([("bounty_id", 1), ("created_at", -1)])
        await self.db.disputes.create_index([("status", 1), ("bounty_id", 1)])

    async def record_delivery(self, delivery_id: str, event_type: str, payload_hash: str) -> bool:
        from pymongo.errors import DuplicateKeyError
        try:
            await self.db.webhook_events.insert_one({"delivery_id": delivery_id, "event_type": event_type, "payload_hash": payload_hash, "status": "received", "created_at": utcnow()})
            return True
        except DuplicateKeyError:
            return False

    async def create_bounty(self, bounty: dict[str, Any]) -> dict[str, Any]:
        from pymongo.errors import DuplicateKeyError

        record = {**bounty, "id": str(uuid4()), "created_at": utcnow(), "updated_at": utcnow()}
        try:
            await self.db.bounties.insert_one(record)
        except DuplicateKeyError as exc:
            raise DuplicateBounty(bounty["contract_bounty_id"]) from exc
        return record

    async def list_bounties(self) -> list[dict[str, Any]]:
        return [item async for item in self.db.bounties.find({}, {"_id": 0}).sort("created_at", -1)]

    async def get_bounty(self, contract_bounty_id: str) -> dict[str, Any] | None:
        return await self.db.bounties.find_one({"contract_bounty_id": contract_bounty_id}, {"_id": 0})

    async def update_bounty(self, contract_bounty_id: str, values: dict[str, Any]) -> None:
        await self.db.bounties.update_one(
            {"contract_bounty_id": contract_bounty_id},
            {"$set": values | {"updated_at": utcnow()}},
        )

    async def find_bounty(self, repository: str) -> dict[str, Any] | None:
        return await self.db.bounties.find_one({"repository": repository, "status": "open"}, {"_id": 0})

    async def create_review(self, review: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        from pymongo.errors import DuplicateKeyError
        record = {**review, "id": str(uuid4()), "created_at": utcnow(), "updated_at": utcnow()}
        try:
            await self.db.reviews.insert_one(record)
            return record, True
        except DuplicateKeyError:
            existing = await self.db.reviews.find_one({"dedupe_key": review["dedupe_key"]}, {"_id": 0})
            return existing, False

    async def update_review(self, review_id: str, values: dict[str, Any]) -> None:
        await self.db.reviews.update_one({"id": review_id}, {"$set": values | {"updated_at": utcnow()}})

    async def get_review(self, review_id: str) -> dict[str, Any] | None:
        return await self.db.reviews.find_one({"id": review_id}, {"_id": 0})

    async def save_agent_results(self, review_id: str, results: list[dict[str, Any]]) -> None:
        if results:
            await self.db.agent_results.insert_many([{"review_id": review_id, **result, "created_at": utcnow()} for result in results])

    async def save_evidence(self, review_id: str, evidence_bytes: bytes, evidence_hash: str, evidence_cid: str) -> None:
        await self.db.evidence.replace_one(
            {"review_id": review_id},
            {
                "review_id": review_id,
                "evidence_bytes": evidence_bytes,
                "evidence_hash": evidence_hash,
                "evidence_cid": evidence_cid,
                "created_at": utcnow(),
            },
            upsert=True,
        )

    async def get_evidence(self, review_id: str) -> dict[str, Any] | None:
        return await self.db.evidence.find_one({"review_id": review_id}, {"_id": 0})

