"""Small in-process worker boundary; replace queue submission in a multi-instance deployment."""
import logging

from .config import Settings
from .github import GitHubAppClient
from .schemas import ReviewInput
from .store import Store
from .workflow import run_review

logger = logging.getLogger(__name__)


async def process_fixture_review(store: Store, review_id: str, review_input: ReviewInput, settings: Settings) -> None:
    try:
        result = await run_review(review_input, settings)
        await store.save_agent_results(review_id, [item.model_dump(mode="json") for item in result.agent_results])
        await store.update_review(review_id, {"status": result.status, "final_score_bps": result.supervisor.final_score_bps,
            "eligible": result.supervisor.eligible, "flagged": result.supervisor.flagged,
            "flag_reasons": result.supervisor.flag_reasons, "evidence_hash": result.evidence_hash})
    except Exception:
        logger.exception("review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})


async def process_github_review(store: Store, review_id: str, review_record: dict, bounty: dict, settings: Settings) -> None:
    try:
        client = GitHubAppClient(settings, review_record.get("github_installation_id"))
        review_input = await client.fetch_review_input(bounty["contract_bounty_id"], review_record["repository"], review_record["pr_number"], bounty["criteria"])
        result = await run_review(review_input, settings)
        await store.save_agent_results(review_id, [item.model_dump(mode="json") for item in result.agent_results])
        await store.update_review(review_id, {"status": result.status, "final_score_bps": result.supervisor.final_score_bps, "eligible": result.supervisor.eligible, "flagged": result.supervisor.flagged, "flag_reasons": result.supervisor.flag_reasons, "evidence_hash": result.evidence_hash})
        if review_record.get("github_check_run_id"):
            await client.complete_check(review_record["repository"], review_record["github_check_run_id"], result)
    except Exception:
        logger.exception("GitHub review worker failed", extra={"review_id": review_id})
        await store.update_review(review_id, {"status": "failed"})
