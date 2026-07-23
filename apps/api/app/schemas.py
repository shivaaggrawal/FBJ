from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentName(str, Enum):
    quality = "quality"
    security = "security"
    spam = "spam"


class Severity(str, Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ChangedFile(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [{
            "path": "src/index.ts",
            "additions": 24,
            "deletions": 3,
        }],
    })

    path: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


class ReviewInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, json_schema_extra={
        "examples": [{
            "bounty_id": "0x1111111111111111111111111111111111111111111111111111111111111111",
            "repository": "owner/demo-repository",
            "pull_request_number": 7,
            "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "title": "Fix payout calculation",
            "body": "Implements the acceptance criteria for the bounty.",
            "diff": "diff --git a/src/index.ts b/src/index.ts\n+export const fixed = true;",
            "changed_files": [{
                "path": "src/index.ts",
                "additions": 24,
                "deletions": 3,
            }],
            "author": "contributor",
            "criteria": "Solution must pass tests and avoid security regressions.",
        }],
    })
    bounty_id: str = Field(min_length=1)
    repository: str = Field(pattern=r"^[^/\s]+/[^/\s]+$")
    pull_request_number: int = Field(gt=0)
    commit_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    title: str = Field(min_length=1, max_length=500)
    body: str | None = None
    diff: str
    changed_files: list[ChangedFile]
    author: str = Field(min_length=1)
    criteria: str = ""


class Finding(BaseModel):
    severity: Severity
    title: str
    explanation: str
    path: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    suggestion: str | None = None

    @field_validator("end_line")
    @classmethod
    def line_range(cls, value: int | None, info):
        if value is not None and info.data.get("start_line") and value < info.data["start_line"]:
            raise ValueError("end_line must not precede start_line")
        return value


class AgentResult(BaseModel):
    agent: AgentName
    score_bps: int = Field(ge=0, le=10_000)
    confidence_bps: int = Field(ge=0, le=10_000)
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    model: str
    prompt_version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None


class SupervisorResult(BaseModel):
    final_score_bps: int = Field(ge=0, le=10_000)
    eligible: bool
    flagged: bool
    flag_reasons: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    schema_version: int = 1
    bounty_id: str
    repository: str
    pr_number: int
    commit_sha: str
    evaluated_at: datetime
    final_score_bps: int = Field(ge=0, le=10_000)
    confidence_bps: int = Field(ge=0, le=10_000)
    agent_scores: list[dict[str, str | int]]
    reasoning: str
    flagged: bool
    flag_reasons: list[str]
    input_truncated: bool = False


class ReviewResponse(BaseModel):
    request_id: str
    review_id: str
    status: str
    supervisor: SupervisorResult
    evidence_hash: str
    commit_sha: str | None = None
    evidence_cid: str | None = None
    attestation_status: str | None = None
    attestation_tx_hash: str | None = None
    agent_results: list[AgentResult] = Field(default_factory=list)


class BountyCreateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "examples": [{
            "contract_bounty_id": "0x1111111111111111111111111111111111111111111111111111111111111111",
            "repository": "owner/demo-repository",
            "issue_url": "https://github.com/owner/demo-repository/issues/1",
            "criteria": "Fix the issue, include tests, and do not introduce security regressions.",
            "reward_token": "0x0000000000000000000000000000000000000000",
            "reward_amount": "1000000",
            "maintainer_wallet": "0x1111111111111111111111111111111111111111",
            "recipient_wallet": "0x2222222222222222222222222222222222222222",
            "expires_at": 1_800_000_000,
            "challenge_seconds": 86400,
        }],
    })

    contract_bounty_id: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    repository: str = Field(pattern=r"^[^/\s]+/[^/\s]+$")
    issue_url: str = Field(min_length=1)
    criteria: str = ""
    reward_token: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    reward_amount: str = Field(pattern=r"^[1-9][0-9]*$")
    maintainer_wallet: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    recipient_wallet: str | None = Field(default=None, pattern=r"^0x[0-9a-fA-F]{40}$")
    expires_at: int = Field(gt=0, description="Unix timestamp passed to BountyEscrow.createBounty.")
    challenge_seconds: int = Field(gt=0)


class BountyRegistrationRequest(BountyCreateRequest):
    creation_tx_hash: str | None = Field(default=None, pattern=r"^0x[0-9a-fA-F]{64}$")
    registration_signature: str | None = Field(default=None, min_length=1)


class BountyResponse(BountyCreateRequest):
    id: str
    status: str
    chain_id: int | None = None
    creation_tx_hash: str | None = None


class BountyRegistrationMessageResponse(BaseModel):
    message: str


class GitHubWebhookResponse(BaseModel):
    request_id: str
    status: str
    delivery_id: str


class DisputeEvidenceRequest(BaseModel):
    evidence: dict[str, Any] = Field(min_length=1)


class DisputeResolutionRequest(BaseModel):
    resolution: int = Field(ge=1, le=2, description="1 pays the recipient; 2 refunds the maintainer.")


class WalletTransactionResponse(BaseModel):
    operation: str
    transaction: dict[str, Any]
    evidence_cid: str | None = None
    evidence_hash: str | None = None
    dispute_status: str | None = None


class TransactionResponse(BaseModel):
    transaction_hash: str
    network: str
    status: str
