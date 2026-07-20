import json
from collections.abc import Mapping

from eth_hash.auto import keccak

from .schemas import AgentResult, EvidenceBundle, Severity, SupervisorResult

_SEVERITY_ORDER = {severity: index for index, severity in enumerate(Severity)}


def canonicalize(value: Mapping[str, object]) -> bytes:
    """Encode deterministic UTF-8 JSON. Lists must be sorted by the caller when order is semantic."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def evidence_hash(evidence_bytes: bytes) -> str:
    return "0x" + keccak(evidence_bytes).hex()


def build_evidence(bundle: EvidenceBundle, agent_results: list[AgentResult]) -> bytes:
    ordered_agents = sorted(agent_results, key=lambda result: result.agent.value)
    agent_scores = []
    for result in ordered_agents:
        findings = sorted(result.findings, key=lambda finding: (
            _SEVERITY_ORDER[finding.severity], finding.path or "", finding.start_line or 0, finding.title
        ))
        agent_scores.append({
            "agent": result.agent.value,
            "scoreBps": result.score_bps,
            "confidenceBps": result.confidence_bps,
            "findings": [finding.model_dump(mode="json", exclude_none=True) for finding in findings],
        })
    payload = bundle.model_dump(mode="json")
    payload["agent_scores"] = agent_scores
    # The blockchain schema uses camelCase.
    payload = {
        "schemaVersion": payload["schema_version"], "bountyId": payload["bounty_id"],
        "repository": payload["repository"], "prNumber": payload["pr_number"],
        "commitSha": payload["commit_sha"], "evaluatedAt": payload["evaluated_at"],
        "finalScoreBps": payload["final_score_bps"], "confidenceBps": payload["confidence_bps"],
        "agentScores": payload["agent_scores"], "reasoning": payload["reasoning"],
        "flagged": payload["flagged"], "flagReasons": payload["flag_reasons"],
    }
    return canonicalize(payload)
