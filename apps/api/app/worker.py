"""Small in-process worker boundary; replace queue submission in a multi-instance deployment."""
import logging

from .config import Settings
from .evidence import evidence_hash
from .ipfs import IpfsClient
from .schemas import ReviewInput
from .store import Store
from .workflow import run_review_artifact

logger = logging.getLogger(__name__)


async def process_fixture_review(store: Store, ipfs: IpfsClient, review_id: str, review_input: ReviewInput, settings: Settings):
    try:
        artifact = await run_review_artifact(review_input, settings)
        result = artifact.response
        calculated_hash = evidence_hash(artifact.evidence_bytes)
        if calculated_hash != result.evidence_hash:
            raise RuntimeError("Evidence hash mismatch before persistence")
        evidence_cid = await ipfs.pin_bytes(artifact.evidence_bytes)
        await store.save_evidence(review_id, artifact.evidence_bytes, calculated_hash, evidence_cid)
        await store.update_review(review_id, {
            "status": result.status,
            "final_score_bps": result.supervisor.final_score_bps,
            "eligible": result.supervisor.eligible,
            "flagged": result.supervisor.flagged,
            "flag_reasons": result.supervisor.flag_reasons,
            "evidence_hash": calculated_hash,
            "evidence_cid": evidence_cid,
            "attestation_status": "pending" if result.supervisor.eligible else "not_eligible",
            "agent_results": [agent.model_dump(mode="json") for agent in artifact.agent_results],
        })
        return result.model_copy(update={"review_id": review_id, "evidence_cid": evidence_cid, "attestation_status": "pending" if result.supervisor.eligible else "not_eligible"})
    except Exception:
        logger.exception("review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})
        raise
