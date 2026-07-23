"""Replay-safe polling of the contracts used as the source of truth for bounty state."""
from __future__ import annotations

import asyncio
import logging

from .chain import ChainClient
from .config import Settings
from .store import Store

logger = logging.getLogger(__name__)


def _bounty_id(event: dict) -> str | None:
    value = event.get("args", {}).get("bountyId", event.get("args", {}).get("bounty_id"))
    return value if isinstance(value, str) else None


async def _apply_event(store: Store, event: dict) -> None:
    bounty_id = _bounty_id(event)
    if bounty_id is None or await store.get_bounty(bounty_id) is None:
        return
    name = event["event"]
    status = {
        "BountyCreated": "open",
        "VerdictSubmitted": "verdict_submitted",
        "VerdictRecorded": "verdict_submitted",
        "BountyChallenged": "challenged",
        "DisputeOpened": "challenged",
        "BountyPaid": "paid_out",
    }.get(name)
    if name == "BountyRefunded":
        status = "cancelled" if event.get("args", {}).get("status") == 6 else "refunded"
    values = {
        "last_chain_event": name,
        "last_chain_tx_hash": event["transaction_hash"],
        "last_chain_block": event["block_number"],
    }
    if status:
        values["status"] = status
    await store.update_bounty(bounty_id, values)


async def sync_chain_events(
    store: Store, chain: ChainClient, chain_id: int, cursor_name: str, from_block: int, to_block: int
) -> int:
    events = await chain.list_events(from_block, to_block)
    applied = 0
    for event in events:
        if await store.record_chain_event(chain_id, event):
            await _apply_event(store, event)
            applied += 1
    await store.save_chain_cursor(cursor_name, to_block + 1)
    return applied


async def monitor_chain_events(store: Store, chain: ChainClient, settings: Settings, stop: asyncio.Event) -> None:
    cursor_name = f"chain-events:{settings.chain_id}"
    while not stop.is_set():
        try:
            latest = await chain.get_latest_block()
            confirmed = latest - settings.chain_event_confirmations
            if confirmed >= 0:
                next_block = await store.get_chain_cursor(cursor_name)
                if next_block is None:
                    next_block = settings.chain_event_start_block if settings.chain_event_start_block is not None else confirmed
                if next_block <= confirmed:
                    count = await sync_chain_events(store, chain, settings.chain_id, cursor_name, next_block, confirmed)
                    logger.info("chain event sync completed", extra={"from_block": next_block, "to_block": confirmed, "events": count})
        except Exception:
            logger.exception("chain event sync failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.chain_event_poll_seconds)
        except TimeoutError:
            continue
