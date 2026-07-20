import asyncio
import json

from app.config import Settings
from app.evidence import canonicalize, evidence_hash
from app.schemas import ReviewInput
from app.workflow import run_review


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


def test_outlier_fixture_is_flagged():
    result = asyncio.run(run_review(sample_review("fixture:flag"), Settings()))
    assert result.status == "flagged"
    assert result.supervisor.flagged
