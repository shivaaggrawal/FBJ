"""Small in-process worker boundary; replace queue submission in a multi-instance deployment."""
import logging

from .config import Settings
from .schemas import ReviewInput
from .store import Store
from .workflow import run_review

logger = logging.getLogger(__name__)


async def process_fixture_review(store: Store, review_id: str, review_input: ReviewInput, settings: Settings) -> None:
    try:
        result = await run_review(review_input, settings)
        await store.update_review(review_id, {"status": result.status, "final_score_bps": result.supervisor.final_score_bps,
            "eligible": result.supervisor.eligible, "flagged": result.supervisor.flagged,
            "flag_reasons": result.supervisor.flag_reasons, "evidence_hash": result.evidence_hash})
    except Exception:
        logger.exception("review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})
