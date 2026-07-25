import asyncio
import json

import pytest

from app.chain import FixtureChainClient
from app.config import Settings
from app.agents import redact_and_truncate
from app.evidence import canonicalize, evidence_hash
from app.ipfs import FixtureIpfsClient
from app.schemas import ReviewInput
from app.store import MemoryStore
from app.worker import persist_review_artifact, process_github_review
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


def test_empty_review_input_is_ineligible_even_in_fixture_mode():
    result = asyncio.run(run_review(sample_review(""), Settings()))
    assert result.status == "flagged"
    assert not result.supervisor.eligible
    assert "No changed files or diff were supplied." in result.supervisor.flag_reasons


def test_non_fixture_configuration_cannot_use_fixture_agent():
    with pytest.raises(ValueError, match="Non-fixture deployments require AI_PROVIDER=groq"):
        Settings(fixture_mode=False, ai_provider="fixture").validate_runtime()


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


def test_persisted_evidence_is_retrieved_and_verified():
    async def exercise():
        store = MemoryStore()
        review_record, _ = await store.create_review({
            "bounty_id": "0x" + "ab" * 32,
            "repository": "fair-bounty/demo",
            "pr_number": 1,
            "commit_sha": "a" * 40,
            "dedupe_key": "evidence-verification",
            "status": "pending",
        })
        result = await persist_review_artifact(
            store,
            FixtureIpfsClient(),
            review_record["id"],
            sample_review(),
            Settings(fixture_mode=True, ai_provider="fixture"),
        )
        evidence = await store.get_evidence(review_record["id"])
        assert evidence is not None
        assert evidence["evidence_hash"] == result.evidence_hash
        assert result.evidence_cid == evidence["evidence_cid"]

    asyncio.run(exercise())


def test_evidence_persistence_rejects_an_ipfs_byte_mutation():
    class CorruptIpfs(FixtureIpfsClient):
        async def fetch_bytes(self, cid: str) -> bytes:
            return b"tampered evidence"

    async def exercise():
        store = MemoryStore()
        review_record, _ = await store.create_review({
            "bounty_id": "0x" + "ab" * 32,
            "repository": "fair-bounty/demo",
            "pr_number": 1,
            "commit_sha": "a" * 40,
            "dedupe_key": "evidence-mutation",
            "status": "pending",
        })
        with pytest.raises(RuntimeError, match="Retrieved IPFS evidence"):
            await persist_review_artifact(
                store,
                CorruptIpfs(),
                review_record["id"],
                sample_review(),
                Settings(fixture_mode=True, ai_provider="fixture"),
            )

    asyncio.run(exercise())


def test_github_worker_pins_evidence_attests_and_completes_check(monkeypatch):
    class FakeGitHubClient:
        completed: list[ReviewInput] = []
        result = None

        def __init__(self, settings: Settings, installation_id: str | int | None = None) -> None:
            pass

        async def fetch_review_input(self, bounty_id: str, repository: str, number: int, criteria: str) -> ReviewInput:
            return sample_review()

        async def complete_check(self, repository: str, check_run_id: int, result) -> None:
            self.result = result
            FakeGitHubClient.result = result

    monkeypatch.setattr("app.worker.GitHubAppClient", FakeGitHubClient)

    async def exercise():
        store = MemoryStore()
        bounty_id = "0x" + "ab" * 32
        bounty = await store.create_bounty({
            "contract_bounty_id": bounty_id,
            "repository": "fair-bounty/demo",
            "criteria": "",
            "recipient_wallet": "0x" + "12" * 20,
            "status": "open",
        })
        review_record, _ = await store.create_review({
            "bounty_id": bounty_id,
            "repository": "fair-bounty/demo",
            "pr_number": 1,
            "commit_sha": "a" * 40,
            "dedupe_key": "github-worker",
            "github_installation_id": "1",
            "github_check_run_id": 99,
            "status": "pending",
        })
        await process_github_review(
            store,
            FixtureIpfsClient(),
            FixtureChainClient(80002),
            review_record["id"],
            review_record,
            bounty,
            Settings(fixture_mode=True, ai_provider="fixture"),
        )
        review = await store.get_review(review_record["id"])
        assert review["attestation_status"] == "confirmed"
        assert review["attestation_tx_hash"].startswith("0x")
        assert FakeGitHubClient.result.evidence_cid.startswith("Qm")
        assert FakeGitHubClient.result.attestation_status == "confirmed"

    asyncio.run(exercise())
