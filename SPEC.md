# Fair Bounty Judge — MVP Technical Specification

## 1. Scope and implementation decisions

This specification defines the smallest demonstrable implementation of the PRD.

- Chain: Polygon Amoy (chain ID 80002); ERC-20 test-token rewards only.
- Storage: MongoDB for mutable workflow state; IPFS for immutable evidence.
- Backend: FastAPI + LangGraph worker.
- Frontend: Next.js/React wallet dashboard.
- GitHub: GitHub App with webhook, Checks, and pull-request comment permissions.
- Disputes: maintainer/reviewer resolution through a backend-authorized contract role; DAO voting is deferred.
- Default policy: final score is the weighted mean of the three agent scores. Any agent score below 40 or a spread greater than 35 points flags the verdict.

## 2. Repository layout

```text
apps/web/                 Next.js dashboard
apps/api/                 FastAPI routes and authentication
workers/review/           LangGraph workflow and agent nodes
packages/schemas/         Shared Pydantic/TypeScript schemas
contracts/                Solidity contracts, tests, deployment scripts
infra/                    Docker Compose, environment templates
tests/                    integration and fixture tests
```

## 3. Core data contracts

### Review input

```json
{
  "bounty_id": "string",
  "repository": "owner/name",
  "pull_request_number": 42,
  "commit_sha": "40-hex-character SHA",
  "title": "string",
  "body": "string|null",
  "diff": "string",
  "changed_files": [{"path": "src/a.ts", "additions": 3, "deletions": 1}],
  "author": "github-login",
  "criteria": "string"
}
```

### Agent result

```json
{
  "agent": "quality|security|spam",
  "score": 0,
  "confidence": 0.0,
  "summary": "string",
  "findings": [{
    "severity": "info|low|medium|high|critical",
    "title": "string",
    "explanation": "string",
    "path": "string|null",
    "start_line": 0,
    "end_line": 0,
    "suggestion": "string|null"
  }],
  "model": "string",
  "prompt_version": "string",
  "created_at": "ISO-8601"
}
```

### Evidence bundle

The JSON must be canonicalized before hashing: UTF-8, sorted object keys, no insignificant whitespace, and deterministic array ordering by agent then finding severity/path/line.

```json
{
  "schema_version": "1.0",
  "bounty_id": "string",
  "repository": "owner/name",
  "pull_request_number": 42,
  "commit_sha": "string",
  "input_sha256": "string",
  "agents": ["AgentResult", "AgentResult", "AgentResult"],
  "final_score": 88,
  "eligible": true,
  "flagged": false,
  "flag_reasons": [],
  "workflow_version": "string",
  "created_at": "ISO-8601"
}
```

`verdict_hash = keccak256(canonical_evidence_json)`. The exact canonical bytes are the source of truth for verification.

## 4. Backend API

All API responses include `request_id`. Mutating endpoints accept an idempotency key.

| Method | Route | Purpose |
|---|---|---|
| POST | `/webhooks/github` | Verify signature, enqueue PR review, return 202 |
| POST | `/api/bounties` | Create operational bounty record after chain transaction |
| GET | `/api/bounties` | List maintainer bounties |
| GET | `/api/bounties/{id}` | Return bounty, verdict, and escrow state |
| GET | `/api/reviews/{id}` | Return review status and agent summaries |
| GET | `/api/reviews/{id}/evidence` | Fetch evidence metadata and IPFS link |
| POST | `/api/reviews/{id}/dispute` | Open a challenge with reason |
| POST | `/api/disputes/{id}/resolve` | Resolve to release or refund |
| POST | `/api/github/checks` | Internal signed callback to publish GitHub result |

Webhook behavior:

1. Validate `X-Hub-Signature-256` with the GitHub App secret.
2. Accept only configured `pull_request` actions (`opened`, `synchronize`, `reopened`).
3. Use `(repository, pr_number, commit_sha)` as the deduplication key.
4. Create/update a pending review and return quickly.
5. Worker posts the completed result asynchronously.

## 5. LangGraph workflow

State fields:

```python
{
  "review_id": str,
  "input": ReviewInput,
  "quality": AgentResult | None,
  "security": AgentResult | None,
  "spam": AgentResult | None,
  "supervisor": SupervisorResult | None,
  "evidence": EvidenceBundle | None,
  "cid": str | None,
  "verdict_tx_hash": str | None,
  "status": str,
  "errors": list[str]
}
```

Graph:

```text
validate_input
      ↓
  ┌── quality ──┐
  ├─ security ──┤ → supervisor → [flag_review | attest]
  └── spam ─────┘                         ↓
                                    publish_github
```

Each agent has a timeout and one retry. Invalid structured output is converted to a failed agent result and causes a flagged review. The supervisor never silently drops an agent.

## 6. MongoDB data model

Use five collections. Store MongoDB `ObjectId` values internally, while keeping blockchain bounty IDs and GitHub delivery IDs as explicit indexed fields.

- `bounties`: chain ID, contract bounty ID, repository, issue URL, criteria, reward token, reward amount, maintainer wallet, payout wallet, challenge seconds, status, and timestamps.
- `reviews`: bounty ID, repository, PR number, commit SHA, unique dedupe key, status, final score, eligibility, flags, CID, verdict hash, transaction hash, timestamps, and agent summaries.
- `agent_results`: review ID, agent name, full structured result, score, confidence, model, prompt version, and timestamp.
- `disputes`: review ID, bounty ID, opener, reason/CID, status, resolution, resolution transaction hash, and timestamps.
- `webhook_events`: unique GitHub delivery ID, event type, payload hash, processing status, error, and processed timestamp.

Required indexes:

- Unique `webhook_events.delivery_id`.
- Unique `reviews.dedupe_key`.
- Compound `bounties.repository + bounties.status`.
- Compound `reviews.bounty_id + reviews.created_at`.
- `disputes.status` and `disputes.bounty_id`.

Use MongoDB transactions only for closely related operational updates, such as recording a webhook and creating its review. Blockchain transactions remain the source of truth for escrow state; database records must be recoverable through event reconciliation.

## 7. Smart contracts

### `BountyEscrow`

Functions:

- `createBounty(bytes32 bountyId, address token, uint128 amount, uint64 expiresAt)` after ERC-20 allowance approval.
- `releaseBounty(bytes32 bountyId)` after the registry's challenge deadline.
- `getBounty(bytes32 bountyId) view returns (Bounty)`.
- The registry and dispute manager are separately role-authorized to record verdicts and settle disputes.

Events:

- `BountyCreated(bountyId, maintainer, token, amount, expiresAt)`
- `VerdictRecorded(bountyId, recipient, releaseAt)`
- `BountyChallenged(bountyId)`
- `BountyPaid(bountyId, recipient, amount)` / `BountyRefunded(bountyId, maintainer, amount, status)`

### `VerdictRegistry`

- `submitVerdict(bytes32 bountyId, bytes32 evidenceHash, string cid, address recipient, uint16 scoreBps)`
- `getVerdict(bytes32 bountyId) view returns (Verdict)`
- Event: `VerdictSubmitted(bountyId, evidenceHash, cid, recipient, scoreBps, challengeDeadline)`

The attestation service is the only authorized publisher. Contract roles, reentrancy protection, checked effects, and one-time settlement are mandatory.

## 8. Security and privacy

- Store GitHub secrets, RPC keys, IPFS credentials, and signer keys only in environment-backed secret storage.
- Signer service exposes no private key to the API process; MVP may use a dedicated testnet account.
- Enforce repository allowlisting and GitHub installation ownership.
- Redact tokens, credentials, and probable secrets before agent calls and IPFS pinning.
- Limit diff size; record truncation in the evidence bundle.
- Treat agent output as untrusted text; escape Markdown and never execute suggestions.
- Require server-side authorization for dispute resolution and verify wallet ownership.

## 9. Testing strategy

- Contract unit tests: funding, unauthorized calls, challenge timing, double settlement, dispute resolution, reentrancy.
- API tests: invalid signature, replay delivery, duplicate PR event, malformed payload, authorization.
- Workflow tests: all agents succeed, one agent fails, outlier flag, deterministic fixture mode, retry behavior.
- Evidence tests: canonicalization produces stable bytes; IPFS bytes hash to the on-chain hash.
- End-to-end test: create bounty → webhook → check → verdict → challenge window → release.
- Manual demo test: disputed verdict blocks payout and resolution settles exactly once.

## 10. Observability and operations

Log with `request_id`, `delivery_id`, `review_id`, `bounty_id`, and `commit_sha`; never log secrets or full diffs. Track webhook latency, workflow duration, agent failure rate, IPFS errors, chain transaction status, and pending challenges. Provide a fixture mode that uses deterministic agent results and a local IPFS/chain adapter.

## 11. Definition of done

The MVP is complete when the acceptance criteria in `PRD.md` pass in fixture mode and on the selected testnet, the evidence verifier reproduces the on-chain hash, the happy-path payout and dispute path are demonstrated, and setup instructions can reproduce the demo from a clean environment.
