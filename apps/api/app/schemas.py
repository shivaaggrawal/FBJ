from datetime import datetime, timezone
from enum import Enum

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
    path: str
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)


class ReviewInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
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


class ReviewResponse(BaseModel):
    request_id: str
    review_id: str
    status: str
    supervisor: SupervisorResult
    evidence_hash: str


class BountyCreateRequest(BaseModel):
    contract_bounty_id: str = Field(min_length=1)
    repository: str = Field(pattern=r"^[^/\s]+/[^/\s]+$")
    issue_url: str = Field(min_length=1)
    criteria: str = ""
    reward_token: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    reward_amount: str = Field(pattern=r"^[0-9]+$")
    maintainer_wallet: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    recipient_wallet: str | None = Field(default=None, pattern=r"^0x[0-9a-fA-F]{40}$")
    challenge_seconds: int = Field(gt=0)


class BountyResponse(BountyCreateRequest):
    id: str
    status: str


class GitHubWebhookResponse(BaseModel):
    request_id: str
    status: str
    delivery_id: str
