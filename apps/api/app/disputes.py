"""Prepare wallet-authorized dispute actions and retain their evidence trail."""
from __future__ import annotations

from typing import Any

from .chain import ChainClient, ChainError
from .evidence import canonicalize, evidence_hash
from .ipfs import IpfsClient
from .store import DuplicateDispute, Store


class DisputeError(RuntimeError):
    pass


async def prepare_open_dispute(
    store: Store, chain: ChainClient, ipfs: IpfsClient, bounty_id: str, evidence: dict[str, Any]
) -> dict[str, Any]:
    if await store.get_bounty(bounty_id) is None:
        raise DisputeError("Bounty was not found")
    evidence_bytes = canonicalize(evidence)
    calculated_hash = evidence_hash(evidence_bytes)
    try:
        evidence_cid = await ipfs.pin_bytes(evidence_bytes)
        if evidence_hash(await ipfs.fetch_bytes(evidence_cid)) != calculated_hash:
            raise DisputeError("Retrieved dispute evidence does not match its canonical hash")
        transaction = await chain.prepare_open_dispute(bounty_id, evidence_cid)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc
    try:
        await store.create_dispute({
            "bounty_id": bounty_id,
            "status": "transaction_prepared",
            "evidence_cid": evidence_cid,
            "evidence_hash": calculated_hash,
            "evidence_bytes": evidence_bytes,
        })
    except DuplicateDispute as exc:
        raise DisputeError("A dispute record already exists for this bounty") from exc
    return {"transaction": transaction, "evidence_cid": evidence_cid, "evidence_hash": calculated_hash}


async def prepare_dispute_resolution(chain: ChainClient, bounty_id: str, resolution: int) -> dict[str, Any]:
    try:
        return await chain.prepare_dispute_resolution(bounty_id, resolution)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc


async def prepare_cancel_open_bounty(chain: ChainClient, bounty_id: str) -> dict[str, Any]:
    try:
        return await chain.prepare_cancel_open_bounty(bounty_id)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc


async def prepare_refund_expired_bounty(chain: ChainClient, bounty_id: str) -> dict[str, Any]:
    try:
        return await chain.prepare_refund_expired_bounty(bounty_id)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc
