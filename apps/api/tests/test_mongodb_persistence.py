import asyncio
import os
from uuid import uuid4

import pytest

from app.store import MongoStore


def test_mongodb_store_persists_state_across_store_restarts():
    async def exercise():
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            from pymongo.errors import ServerSelectionTimeoutError

            probe = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=750)
            await probe.admin.command("ping")
            probe.close()
        except ServerSelectionTimeoutError:
            pytest.skip("MongoDB is not reachable at MONGODB_URI")

        database = f"fbj_persistence_test_{uuid4().hex}"
        first = MongoStore(uri, database)
        second = None
        try:
            await first.ensure_indexes()
            bounty_id = "0x" + "d1" * 32
            review_record, _ = await first.create_review({
                "bounty_id": bounty_id,
                "repository": "owner/mongo-persistence",
                "pr_number": 7,
                "commit_sha": "a" * 40,
                "dedupe_key": "mongo-persistence-review",
                "status": "completed",
            })
            await first.create_bounty({
                "contract_bounty_id": bounty_id,
                "repository": "owner/mongo-persistence",
                "issue_url": "https://github.com/owner/mongo-persistence/issues/1",
                "criteria": "persist state",
                "reward_token": "0x" + "12" * 20,
                "reward_amount": "1000000",
                "maintainer_wallet": "0x" + "34" * 20,
                "recipient_wallet": "0x" + "56" * 20,
                "expires_at": 1_900_000_000,
                "challenge_seconds": 3600,
                "status": "open",
            })
            await first.save_evidence(review_record["id"], b'{"ok":true}', "0x" + "aa" * 32, "QmPersistenceCid")
            await first.create_dispute({
                "bounty_id": bounty_id,
                "status": "open",
                "evidence_cid": "QmDisputeCid",
                "evidence_hash": "0x" + "bb" * 32,
            })
            assert await first.record_delivery("mongo-delivery", "pull_request", "0xhash") is True
            assert await first.record_delivery("mongo-delivery", "pull_request", "0xhash") is False
            await first.save_chain_cursor("amoy", 12345)
            first.client.close()

            second = MongoStore(uri, database)
            await second.ensure_indexes()

            assert (await second.get_bounty(bounty_id))["status"] == "open"
            assert (await second.find_bounty("owner/mongo-persistence"))["contract_bounty_id"] == bounty_id
            assert (await second.get_review(review_record["id"]))["dedupe_key"] == "mongo-persistence-review"
            evidence = await second.get_evidence(review_record["id"])
            assert evidence["evidence_bytes"] == b'{"ok":true}'
            assert evidence["evidence_cid"] == "QmPersistenceCid"
            assert (await second.get_dispute(bounty_id))["evidence_cid"] == "QmDisputeCid"
            assert await second.get_chain_cursor("amoy") == 12345
        finally:
            cleanup = second or first
            await cleanup.client.drop_database(database)
            cleanup.client.close()

    asyncio.run(exercise())
