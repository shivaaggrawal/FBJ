import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from .config import Settings
from .evidence import build_evidence, evidence_hash
from .schemas import AgentName, AgentResult, EvidenceBundle, ReviewInput, ReviewResponse, SupervisorResult


async def fixture_agent(agent: AgentName, review: ReviewInput, settings: Settings) -> AgentResult:
    await asyncio.sleep(0)
    base_scores = {AgentName.quality: 8400, AgentName.security: 8200, AgentName.spam: 9000}
    score = base_scores[agent]
    if "fixture:flag" in review.diff.lower():
        score = 3500 if agent is AgentName.security else score
    return AgentResult(agent=agent, score_bps=score, confidence_bps=9000, summary=f"Fixture {agent.value} review completed.", model=settings.ai_model, prompt_version="fixture-1")


def supervise(results: list[AgentResult]) -> SupervisorResult:
    scores = [result.score_bps for result in results]
    final_score = round(sum(scores) / len(scores))
    reasons = []
    if any(score < 4000 for score in scores):
        reasons.append("agent score below 4,000 bps")
    if max(scores) - min(scores) > 3500:
        reasons.append("agent score spread exceeds 3,500 bps")
    return SupervisorResult(final_score_bps=final_score, eligible=final_score >= 7000 and not reasons, flagged=bool(reasons), flag_reasons=reasons)


async def run_review(review: ReviewInput, settings: Settings) -> ReviewResponse:
    results = await asyncio.gather(*(fixture_agent(agent, review, settings) for agent in AgentName))
    supervisor = supervise(list(results))
    evidence = EvidenceBundle(bounty_id=review.bounty_id, repository=review.repository, pr_number=review.pull_request_number,
        commit_sha=review.commit_sha, evaluated_at=datetime.now(timezone.utc), final_score_bps=supervisor.final_score_bps,
        confidence_bps=round(sum(r.confidence_bps for r in results) / len(results)), agent_scores=[],
        reasoning="Deterministic fixture workflow; no external AI provider was called.", flagged=supervisor.flagged,
        flag_reasons=supervisor.flag_reasons)
    digest = evidence_hash(build_evidence(evidence, list(results)))
    return ReviewResponse(request_id=str(uuid4()), review_id=str(uuid4()), status="flagged" if supervisor.flagged else "completed", supervisor=supervisor, evidence_hash=digest)
