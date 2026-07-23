# Fair Bounty Judge — Product Requirements Document

## 1. Summary

Fair Bounty Judge is a GitHub-native, AI-assisted crypto bounty settlement system. It evaluates a pull request with independent review agents, aggregates their findings, publishes a cryptographic evidence trail, and releases escrowed funds only after a challenge window. Disputed or anomalous verdicts are paused for human/community review.

## 2. Problem

Crypto bounties improve incentives for open-source work but do not solve trust in review. Maintainers may be slow or inconsistent, contributors cannot easily verify why they were rejected, and AI-generated review is difficult to audit. The product needs a neutral workflow where review evidence is visible, tamper-evident, and connected to the payment state.

## 3. Goals and non-goals

### Goals

- Reduce maintainer review effort.
- Give contributors a fast, GitHub-native verdict.
- Make verdict inputs and reasoning auditable.  
- Enforce transparent escrow, challenge, and payout states.
- Demonstrate useful multi-agent consensus rather than a single opaque score.

### Non-goals

- Replacing maintainers or security professionals.
- Proving that an AI verdict is objectively correct.
- Supporting production custody, mainnet risk, or generalized governance in the MVP.

## 4. Personas and primary journeys

### Maintainer

1. Connect wallet.
2. Paste a GitHub Issue URL, define reward and challenge duration.
3. Deposit testnet funds.
4. Monitor PRs and verdicts.
5. If disputed, inspect evidence and manually resolve/release/refund.

### Developer

1. Open a PR against a bounty-enabled repository.
2. See an in-progress GitHub Check.
3. Receive score, eligibility, findings, and evidence links as a PR comment.
4. Challenge a verdict during the challenge window.

### Reviewer

1. Open a flagged dispute.
2. Compare agent outputs, commit SHA, evidence bundle, and dispute notes.
3. Record a resolution that causes escrow to release or refund.

## 5. Functional requirements

### FR-1 Bounty creation

The system shall allow a connected maintainer to create a bounty containing bounty ID, repository/issue URL, reward amount, accepted criteria, payout wallet, challenge duration, and lifecycle status. The contract shall emit an event with the bounty ID and core metadata.

### FR-2 GitHub ingress

The GitHub App shall receive PR webhook events, verify the signature, identify the configured bounty, capture repository, PR number, head commit SHA, diff, author, and changed files, and reject replayed or malformed events.

### FR-3 Multi-agent review

The workflow shall run quality, security, and spam agents in parallel. Each agent shall return a typed result with score, confidence, findings, severity, file/line references when available, and model/runtime metadata.

### FR-4 Supervision and consensus

The supervisor shall normalize agent outputs into a deterministic schema, calculate a final score, preserve each agent's original result, and flag configurable disagreement/outlier conditions for manual review.

### FR-5 Evidence and attestation

The system shall create a canonical JSON evidence bundle tied to the exact commit SHA. It shall calculate a keccak256 evidence hash, pin the bundle to IPFS, and record the verdict hash, CID, score, bounty ID, and commit reference in `VerdictRegistry`.

### FR-6 Escrow lifecycle

`BountyEscrow` shall support funded, under-review, challenge-open, released, disputed, refunded, and resolved states. It shall prevent payout before the challenge window ends and prevent double settlement.

### FR-7 GitHub feedback

The App shall publish an in-progress check, final check, summary comment, score, eligibility status, inline annotations when line mapping is reliable, and links to IPFS and the blockchain transaction.

### FR-8 Dashboard

The dashboard shall show active bounties, PR verdict history, agent score breakdown, evidence bundle, transaction status, challenge countdown, and dispute actions available to the maintainer/reviewer.

## 6. Non-functional requirements

- Security: verify GitHub signatures; never expose private keys; use least-privilege GitHub permissions; validate all contract inputs.
- Reliability: webhook processing must be idempotent; workflow retries must not create duplicate payouts or attestations.
- Auditability: retain immutable references to repository, PR, commit SHA, prompt/version metadata, agent results, canonical bundle, CID, and transaction hashes.
- Performance: show an in-progress check immediately; target a demo verdict within 2 minutes for a small PR.
- Privacy: do not place secrets in prompts or IPFS; document that submitted code/diffs are processed by configured AI providers.
- Accessibility: dashboard and GitHub output must be readable without relying on color alone.

## 7. Proposed technical design

Frontend: Next.js/React with wallet connection and maintainer dashboard.

Backend: FastAPI webhook/API layer, PostgreSQL for operational state, LangGraph for orchestration.

Agents: quality, security, and spam nodes with structured JSON outputs.

Storage: IPFS for evidence bundles; database stores operational records and CID.

Blockchain: Solidity `BountyEscrow`, `VerdictRegistry`, and a minimal `DisputeManager` on one EVM testnet.

Integrations: GitHub App, GitHub Checks/Comments API, EVM RPC, wallet provider, IPFS pinning provider.

## 8. State flow

`FUNDED → PR_RECEIVED → ANALYZING → VERDICT_PUBLISHED → CHALLENGE_OPEN → RELEASED`

Exception paths: `ANALYZING → FLAGGED_FOR_REVIEW`, `CHALLENGE_OPEN → DISPUTED → RESOLVED_RELEASE` or `RESOLVED_REFUND`.

## 9. Acceptance criteria for the demo

- A maintainer funds a bounty from the UI and sees the contract event.
- A real or fixture PR triggers the workflow exactly once.
- All three agents return results and the GitHub Check changes from in-progress to completed.
- The final comment includes score, eligibility, findings, commit SHA, CID, and attestation transaction.
- The evidence bundle retrieved from IPFS hashes to the on-chain verdict hash.
- The contract releases funds only after the configured challenge window.
- A disagreement fixture creates a flagged/disputed state and blocks automatic payout.

## 10. Risks and mitigations

- AI false positives: show independent findings, confidence, and human challenge path.
- Prompt/output drift: use strict schemas, version prompts, and hash canonical output.
- GitHub diff size: cap input, summarize safely, and disclose truncation.
- Smart-contract bugs: keep contracts minimal, test locally, use testnet only, and add reentrancy/access controls.
- Demo dependency failure: provide deterministic fixture mode for agent, IPFS, and chain integrations.

## 11. Open decisions

- Which EVM testnet and IPFS provider will be used?
- What score threshold means bounty-eligible?
- What exact disagreement rule triggers manual review?
- Will disputes be maintainer-resolved for MVP or include a lightweight reviewer role?
- Which model/provider is used for each agent, and what data-retention settings apply?
