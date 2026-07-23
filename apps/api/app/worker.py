"""Small in-process worker boundary; replace queue submission in a multi-instance deployment."""
import logging
from typing import Any

from .attestation import AttestationError, attest_review
from .chain import ChainClient
from .config import Settings
from .evidence import evidence_hash
from .github import GitHubAppClient
from .ipfs import IpfsClient
from .schemas import ReviewInput, ReviewResponse
from .store import Store
from .workflow import run_review_artifact

logger = logging.getLogger(__name__)


async def persist_review_artifact(
    store: Store,
    ipfs: IpfsClient,
    review_id: str,
    review_input: ReviewInput,
    settings: Settings,
) -> ReviewResponse:
    """Run a review, verify its pinned evidence, and persist the auditable result."""
    artifact = await run_review_artifact(review_input, settings)
    result = artifact.response
    calculated_hash = evidence_hash(artifact.evidence_bytes)
    if calculated_hash != result.evidence_hash:
        raise RuntimeError("Evidence hash mismatch before persistence")

    evidence_cid = await ipfs.pin_bytes(artifact.evidence_bytes)
    if evidence_hash(await ipfs.fetch_bytes(evidence_cid)) != calculated_hash:
        raise RuntimeError("Retrieved IPFS evidence does not match the canonical evidence hash")

    await store.save_evidence(review_id, artifact.evidence_bytes, calculated_hash, evidence_cid)
    await store.save_agent_results(review_id, [agent.model_dump(mode="json") for agent in artifact.agent_results])

    attestation_status = "pending" if result.supervisor.eligible else "not_eligible"
    await store.update_review(review_id, {
        "status": result.status,
        "final_score_bps": result.supervisor.final_score_bps,
        "eligible": result.supervisor.eligible,
        "flagged": result.supervisor.flagged,
        "flag_reasons": result.supervisor.flag_reasons,
        "evidence_hash": calculated_hash,
        "evidence_cid": evidence_cid,
        "attestation_status": attestation_status,
    })
    return result.model_copy(update={
        "review_id": review_id,
        "evidence_cid": evidence_cid,
        "attestation_status": attestation_status,
        "agent_results": artifact.agent_results,
    })


async def process_fixture_review(
    store: Store,
    ipfs: IpfsClient,
    review_id: str,
    review_input: ReviewInput,
    settings: Settings,
) -> ReviewResponse | None:
    try:
        return await persist_review_artifact(store, ipfs, review_id, review_input, settings)
    except Exception:
        logger.exception("review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})
        return None


async def process_github_review(
    store: Store,
    ipfs: IpfsClient,
    chain: ChainClient,
    review_id: str,
    review_record: dict[str, Any],
    bounty: dict[str, Any],
    settings: Settings,
) -> None:
    try:
        client = GitHubAppClient(settings, review_record.get("github_installation_id"))
        review_input = await client.fetch_review_input(bounty["contract_bounty_id"], review_record["repository"], review_record["pr_number"], bounty["criteria"])
        result = await persist_review_artifact(store, ipfs, review_id, review_input, settings)

        if result.supervisor.eligible and bounty.get("recipient_wallet"):
            try:
                transaction = await attest_review(store, chain, ipfs, review_id)
                result = result.model_copy(update={
                    "attestation_status": "confirmed",
                    "attestation_tx_hash": transaction["transaction_hash"],
                })
            except AttestationError as exc:
                logger.warning("review attestation failed", extra={"review_id": review_id, "error": str(exc)})
                result = result.model_copy(update={"attestation_status": "failed"})
        elif result.supervisor.eligible:
            await store.update_review(review_id, {"attestation_status": "recipient_required"})
            result = result.model_copy(update={"attestation_status": "recipient_required"})

        if review_record.get("github_check_run_id"):
            await client.complete_check(review_record["repository"], review_record["github_check_run_id"], result)
    except Exception:
        logger.exception("GitHub review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})
        raise
