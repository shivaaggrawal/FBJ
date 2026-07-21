import asyncio
import json

from app.config import Settings
from app.agents import redact_and_truncate
from app.evidence import canonicalize, evidence_hash
from app.schemas import ReviewInput
from app.workflow import build_review_graph, run_review


def sample_review(diff: str = "diff --git a/a.py b/a.py") -> ReviewInput:
    return ReviewInput(bounty_id="0x" + "ab" * 32, repository="fair-bounty/demo", pull_request_number=1,
        commit_sha="a" * 40, title="Test", diff=diff, changed_files=[], author="developer")


def test_canonicalization_and_keccak_are_stable():
    assert canonicalize({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert evidence_hash(b"") == "0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_fixture_workflow_is_eligible():
    result = asyncio.run(run_review(sample_review(), Settings()))
    assert result.status == "completed"
    assert result.supervisor.final_score_bps == 8533
    assert result.supervisor.eligible


def test_langgraph_defines_parallel_agent_nodes():
    graph = build_review_graph()
    node_names = set(graph.get_graph().nodes)
    assert {"validate_input", "run_quality", "run_security", "run_spam", "run_supervisor"} <= node_names


def test_outlier_fixture_is_flagged():
    result = asyncio.run(run_review(sample_review("fixture:flag"), Settings()))
    assert result.status == "flagged"
    assert result.supervisor.flagged


def test_redaction_and_truncation_keep_secrets_out_of_prompts():
    result, truncated = redact_and_truncate("API_KEY=top-secret\nBearer abcdefghijklmnopqrstuvwxyz", 12)
    assert "top-secret" not in result
    assert "abcdefghijklmnopqrstuvwxyz" not in result
    assert truncated
