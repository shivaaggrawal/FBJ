import asyncio

import pytest

from app.chain import ChainError, FixtureChainClient
from app.event_indexer import sync_chain_events
from app.store import MemoryStore


BOUNTY_ID = "0x" + "ab" * 32
EVIDENCE_HASH = "0x" + "cd" * 32
CID = "Qm" + "a" * 44


def test_fixture_chain_prepares_wallet_actions_and_exposes_chain_events():
    async def run() -> None:
        chain = FixtureChainClient(80002)

        creation = await chain.prepare_bounty_creation(BOUNTY_ID, "0x" + "12" * 20, 1_000_000, 1_900_000_000)
        assert creation["approval"]["operation"] == "approve"
        assert creation["create"]["operation"] == "create_bounty"
        assert (await chain.prepare_open_dispute(BOUNTY_ID, CID))["operation"] == "open_dispute"
        assert (await chain.prepare_cancel_open_bounty(BOUNTY_ID))["operation"] == "cancel_open_bounty"
        assert (await chain.prepare_dispute_resolution(BOUNTY_ID, 1))["operation"] == "resolve_dispute"

        await chain.submit_verdict(BOUNTY_ID, EVIDENCE_HASH, CID, "0x" + "34" * 20, 8_500)
        events = await chain.list_events(0)
        assert events[0]["event"] == "VerdictSubmitted"
        assert (await chain.get_dispute(BOUNTY_ID))["open"] is False
        opened = await chain.confirm_open_dispute(BOUNTY_ID, CID, "0x" + "11" * 32)
        assert opened["status"] == "confirmed"
        assert (await chain.get_dispute(BOUNTY_ID))["open"] is True
        assert (await chain.resolve_dispute(BOUNTY_ID, 2))["status"] == "confirmed"
        assert (await chain.get_dispute(BOUNTY_ID))["resolution"] == 2
        assert (await chain.get_transaction_status(opened["transaction_hash"]))["status"] == "confirmed"
        assert (await chain.refund_expired_bounty(BOUNTY_ID))["status"] == "confirmed"

    asyncio.run(run())


def test_fixture_chain_rejects_invalid_dispute_requests():
    async def run() -> None:
        chain = FixtureChainClient(80002)
        with pytest.raises(ChainError, match="Evidence CID"):
            await chain.prepare_open_dispute(BOUNTY_ID, "not-a-cid")
        with pytest.raises(ChainError, match="resolution"):
            await chain.prepare_dispute_resolution(BOUNTY_ID, 0)
        with pytest.raises(ChainError, match="Invalid block range"):
            await chain.list_events(10, 9)

    asyncio.run(run())


def test_event_indexer_updates_known_bounties_and_ignores_replays():
    async def run() -> None:
        chain = FixtureChainClient(80002)
        store = MemoryStore()
        await store.create_bounty({"contract_bounty_id": BOUNTY_ID, "repository": "owner/repository", "status": "open"})
        await chain.submit_verdict(BOUNTY_ID, EVIDENCE_HASH, CID, "0x" + "34" * 20, 8_500)

        assert await sync_chain_events(store, chain, 80002, "chain-events:80002", 0, 1) == 1
        assert (await store.get_bounty(BOUNTY_ID))["status"] == "verdict_submitted"
        assert await store.get_chain_cursor("chain-events:80002") == 2
        assert await sync_chain_events(store, chain, 80002, "chain-events:80002", 0, 1) == 0

    asyncio.run(run())


def test_event_indexer_reconciles_dispute_lifecycle():
    async def run() -> None:
        chain = FixtureChainClient(80002)
        store = MemoryStore()
        await store.create_bounty({"contract_bounty_id": BOUNTY_ID, "repository": "owner/repository", "status": "verdict_submitted"})
        await store.create_dispute({"bounty_id": BOUNTY_ID, "status": "transaction_prepared", "evidence_cid": CID})

        await chain.confirm_open_dispute(BOUNTY_ID, CID, "0x" + "55" * 32)
        await chain.confirm_dispute_resolution(BOUNTY_ID, 1, "0x" + "66" * 32)

        assert await sync_chain_events(store, chain, 80002, "chain-events:disputes", 0, 1) == 4
        dispute = await store.get_dispute(BOUNTY_ID)
        assert dispute["status"] == "resolved"
        assert dispute["resolution"] == 1
        assert (await store.get_bounty(BOUNTY_ID))["status"] == "paid_out"

    asyncio.run(run())
