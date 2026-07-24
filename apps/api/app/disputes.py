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


async def confirm_open_dispute(store: Store, chain: ChainClient, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
    dispute = await store.get_dispute(bounty_id)
    if dispute is None:
        raise DisputeError("Prepare dispute evidence before confirming its transaction")
    try:
        result = await chain.confirm_open_dispute(bounty_id, dispute["evidence_cid"], transaction_hash)
    except ChainError as exc:
        await store.update_dispute(bounty_id, {"status": "transaction_failed", "transaction_hash": transaction_hash, "transaction_error": str(exc)})
        raise DisputeError(str(exc)) from exc
    values = {"transaction_hash": result["transaction_hash"], "transaction_status": result["status"]}
    if result["status"] == "confirmed":
        values["status"] = "opened"
        await store.update_bounty(bounty_id, {"status": "challenged", "dispute_tx_hash": result["transaction_hash"]})
    elif result["status"] == "failed":
        values |= {"status": "transaction_failed", "transaction_error": result.get("error", "Transaction reverted")}
    else:
        values["status"] = "transaction_pending"
    await store.update_dispute(bounty_id, values)
    return result


async def confirm_dispute_resolution(
    store: Store, chain: ChainClient, bounty_id: str, resolution: int, transaction_hash: str
) -> dict[str, Any]:
    try:
        result = await chain.confirm_dispute_resolution(bounty_id, resolution, transaction_hash)
    except ChainError as exc:
        dispute = await store.get_dispute(bounty_id)
        if dispute is not None:
            await store.update_dispute(bounty_id, {"status": "transaction_failed", "resolution_tx_hash": transaction_hash, "transaction_error": str(exc)})
        raise DisputeError(str(exc)) from exc
    await _record_dispute_resolution(store, bounty_id, resolution, result)
    return result


async def confirm_cancel_open_bounty(store: Store, chain: ChainClient, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
    try:
        result = await chain.confirm_cancel_open_bounty(bounty_id, transaction_hash)
    except ChainError as exc:
        await store.update_bounty(bounty_id, {"cancellation_status": "failed", "cancellation_tx_hash": transaction_hash, "cancellation_error": str(exc)})
        raise DisputeError(str(exc)) from exc
    values = {"cancellation_status": result["status"], "cancellation_tx_hash": result["transaction_hash"]}
    if result["status"] == "confirmed":
        values["status"] = "cancelled"
    elif result["status"] == "failed":
        values["cancellation_error"] = result.get("error", "Transaction reverted")
    await store.update_bounty(bounty_id, values)
    return result


async def confirm_refund_expired_bounty(store: Store, chain: ChainClient, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
    try:
        result = await chain.confirm_refund_expired_bounty(bounty_id, transaction_hash)
    except ChainError as exc:
        await store.update_bounty(bounty_id, {"refund_status": "failed", "refund_tx_hash": transaction_hash, "refund_error": str(exc)})
        raise DisputeError(str(exc)) from exc
    values = {"refund_status": result["status"], "refund_tx_hash": result["transaction_hash"]}
    if result["status"] == "confirmed":
        values["status"] = "refunded"
    elif result["status"] == "failed":
        values["refund_error"] = result.get("error", "Transaction reverted")
    await store.update_bounty(bounty_id, values)
    return result


async def resolve_dispute_with_service(store: Store, chain: ChainClient, bounty_id: str, resolution: int) -> dict[str, Any]:
    try:
        result = await chain.resolve_dispute(bounty_id, resolution)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc
    await _record_dispute_resolution(store, bounty_id, resolution, result)
    return result


async def refund_expired_bounty_with_service(store: Store, chain: ChainClient, bounty_id: str) -> dict[str, Any]:
    try:
        result = await chain.refund_expired_bounty(bounty_id)
    except ChainError as exc:
        raise DisputeError(str(exc)) from exc
    values = {"refund_status": result["status"], "refund_tx_hash": result["transaction_hash"]}
    if result["status"] == "confirmed":
        values["status"] = "refunded"
    elif result["status"] == "failed":
        values["refund_error"] = result.get("error", "Transaction reverted")
    await store.update_bounty(bounty_id, values)
    return result


async def _record_dispute_resolution(store: Store, bounty_id: str, resolution: int, result: dict[str, Any]) -> None:
    dispute = await store.get_dispute(bounty_id)
    if dispute is not None:
        values = {"resolution": resolution, "resolution_tx_hash": result["transaction_hash"], "resolution_transaction_status": result["status"]}
        if result["status"] == "confirmed":
            values["status"] = "resolved"
        elif result["status"] == "failed":
            values |= {"status": "transaction_failed", "transaction_error": result.get("error", "Transaction reverted")}
        else:
            values["status"] = "resolution_pending"
        await store.update_dispute(bounty_id, values)
    if result["status"] == "confirmed":
        await store.update_bounty(bounty_id, {"status": "paid_out" if resolution == 1 else "refunded", "resolution_tx_hash": result["transaction_hash"]})
