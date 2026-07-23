"""Coordinates persisted evidence with the VerdictRegistry and BountyEscrow contracts."""
from __future__ import annotations

from typing import Any

from .chain import ChainClient, ChainError
from .evidence import evidence_hash
from .ipfs import IpfsClient
from .store import Store


class AttestationError(RuntimeError):
    pass


async def attest_review(store: Store, chain: ChainClient, ipfs: IpfsClient, review_id: str) -> dict[str, Any]:
    review = await store.get_review(review_id)
    if review is None:
        raise AttestationError("Review was not found")
    if review.get("status") != "completed" or not review.get("eligible") or review.get("flagged"):
        raise AttestationError("Only completed, eligible, unflagged reviews can be attested")
    evidence = await store.get_evidence(review_id)
    if evidence is None:
        raise AttestationError("Review evidence has not been persisted")
    if evidence_hash(evidence["evidence_bytes"]) != evidence["evidence_hash"]:
        raise AttestationError("Persisted evidence does not match its attestation hash")
    try:
        retrieved_hash = evidence_hash(await ipfs.fetch_bytes(evidence["evidence_cid"]))
    except Exception as exc:
        raise AttestationError("Evidence CID could not be retrieved before attestation") from exc
    if retrieved_hash != evidence["evidence_hash"]:
        raise AttestationError("Retrieved IPFS evidence does not match its attestation hash")
    if review.get("attestation_status") == "confirmed":
        raise AttestationError("Review has already been attested")
    bounty = await store.get_bounty(review["bounty_id"])
    if bounty is None:
        raise AttestationError("Bounty was not found")
    recipient_wallet = bounty.get("recipient_wallet")
    if not recipient_wallet:
        raise AttestationError("Bounty recipient_wallet must be verified before attestation")
    try:
        result = await chain.submit_verdict(review["bounty_id"], evidence["evidence_hash"], evidence["evidence_cid"], recipient_wallet, review["final_score_bps"])
    except ChainError as exc:
        await store.update_review(review_id, {"attestation_status": "failed", "attestation_error": str(exc)})
        raise AttestationError(str(exc)) from exc
    await store.update_review(review_id, {"attestation_status": "confirmed", "recipient_wallet": recipient_wallet, "attestation_tx_hash": result["transaction_hash"]})
    await store.update_bounty(review["bounty_id"], {"status": "verdict_submitted", "verdict_review_id": review_id, "verdict_tx_hash": result["transaction_hash"]})
    return result


async def release_bounty(store: Store, chain: ChainClient, contract_bounty_id: str) -> dict[str, Any]:
    bounty = await store.get_bounty(contract_bounty_id)
    if bounty is None:
        raise AttestationError("Bounty was not found")
    try:
        result = await chain.release_bounty(contract_bounty_id)
    except ChainError as exc:
        raise AttestationError(str(exc)) from exc
    await store.update_bounty(contract_bounty_id, {"status": "paid_out", "release_tx_hash": result["transaction_hash"]})
    return result
