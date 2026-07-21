import asyncio
from datetime import datetime, timezone
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from .agents import groq_agent, redact_and_truncate
from .config import Settings
from .evidence import build_evidence, evidence_hash
from .schemas import AgentName, AgentResult, EvidenceBundle, ReviewInput, ReviewResponse, SupervisorResult


class ReviewGraphState(TypedDict, total=False):
    """State passed between LangGraph review nodes."""
    review: ReviewInput
    settings: Settings
    quality: AgentResult
    security: AgentResult
    spam: AgentResult
    supervisor: SupervisorResult
    evidence_hash: str
    input_truncated: bool
    errors: list[str]


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
    if any(result.error for result in results):
        reasons.append("one or more review agents failed")
    return SupervisorResult(final_score_bps=final_score, eligible=final_score >= 7000 and not reasons, flagged=bool(reasons), flag_reasons=reasons)


async def validate_input(state: ReviewGraphState) -> dict:
    review = state["review"]
    errors = []
    if not review.changed_files and not review.diff:
        errors.append("No changed files or diff were supplied.")
    _, input_truncated = redact_and_truncate(review.diff, state["settings"].ai_max_diff_chars)
    return {"errors": errors, "input_truncated": input_truncated}


async def _run_agent(state: ReviewGraphState, agent: AgentName) -> AgentResult:
    settings = state["settings"]
    agent_function = groq_agent if settings.ai_provider == "groq" else fixture_agent
    return await agent_function(agent, state["review"], settings)


async def quality_node(state: ReviewGraphState) -> dict:
    return {"quality": await _run_agent(state, AgentName.quality)}


async def security_node(state: ReviewGraphState) -> dict:
    return {"security": await _run_agent(state, AgentName.security)}


async def spam_node(state: ReviewGraphState) -> dict:
    return {"spam": await _run_agent(state, AgentName.spam)}


async def supervisor_node(state: ReviewGraphState) -> dict:
    results = [state["quality"], state["security"], state["spam"]]
    supervisor = supervise(results)
    review = state["review"]
    evidence = EvidenceBundle(bounty_id=review.bounty_id, repository=review.repository, pr_number=review.pull_request_number,
        commit_sha=review.commit_sha, evaluated_at=datetime.now(timezone.utc), final_score_bps=supervisor.final_score_bps,
        confidence_bps=round(sum(result.confidence_bps for result in results) / len(results)), agent_scores=[],
        reasoning="Independent LangGraph agent results were combined by the deterministic supervisor.", flagged=supervisor.flagged,
        flag_reasons=supervisor.flag_reasons, input_truncated=state["input_truncated"])
    return {"supervisor": supervisor, "evidence_hash": evidence_hash(build_evidence(evidence, results))}


def build_review_graph():
    graph = StateGraph(ReviewGraphState)
    graph.add_node("validate_input", validate_input)
    graph.add_node("run_quality", quality_node)
    graph.add_node("run_security", security_node)
    graph.add_node("run_spam", spam_node)
    graph.add_node("run_supervisor", supervisor_node)
    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input", lambda _: ["run_quality", "run_security", "run_spam"])
    graph.add_edge("run_quality", "run_supervisor")
    graph.add_edge("run_security", "run_supervisor")
    graph.add_edge("run_spam", "run_supervisor")
    graph.add_edge("run_supervisor", END)
    return graph.compile()


async def run_review(review: ReviewInput, settings: Settings) -> ReviewResponse:
    final_state = await build_review_graph().ainvoke({"review": review, "settings": settings, "errors": []})
    results = [final_state["quality"], final_state["security"], final_state["spam"]]
    supervisor = final_state["supervisor"]
    return ReviewResponse(request_id=str(uuid4()), review_id=str(uuid4()), status="flagged" if supervisor.flagged else "completed", supervisor=supervisor, evidence_hash=final_state["evidence_hash"], agent_results=results)
