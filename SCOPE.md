# Fair Bounty Judge — MVP Scope

## Product promise

Fair Bounty Judge makes GitHub bounty payouts more trustworthy by combining parallel AI review, reproducible evidence, and an on-chain challenge window.

## Target users

- Repository maintainers who fund GitHub issues with crypto.
- Developers who submit pull requests for those issues.
- Optional community reviewers who resolve disputed verdicts.

## Hackathon MVP outcome

For one repository, one bounty, and one supported EVM testnet, a maintainer can fund a bounty, a GitHub PR can trigger an automated review, and the system can publish a tamper-evident verdict that controls a testnet escrow payout after a challenge period.

## In scope

1. Maintainer connects a wallet and creates a bounty from a GitHub Issue URL.
2. BountyEscrow contract accepts a native-token deposit and emits `BountyCreated`.
3. GitHub App/webhook receives PR metadata, diff, commit SHA, and bounty ID.
4. FastAPI validates the webhook and starts a LangGraph workflow.
5. Three parallel agents produce structured findings:
   - Code quality
   - Security
   - Spam/low-effort detection
6. Supervisor normalizes scores, detects major disagreement, and creates an evidence bundle.
7. Trust & Attestation step hashes the canonical bundle, stores it on IPFS, and submits verdict metadata to `VerdictRegistry`.
8. Escrow opens a challenge window and releases funds on the happy path.
9. GitHub App posts a pending check, final summary, inline findings where feasible, and links to IPFS/blockchain evidence.
10. Minimal dashboard shows active bounties, verdict history, evidence, and disputes.

## Explicitly out of scope for MVP

- Production-grade DAO governance, token voting, or multi-sig administration.
- Multi-chain deployment.
- Fully autonomous dispute resolution.
- Arbitrary repository permissions and enterprise GitHub installations.
- Guaranteed one-click code commits from suggestions.
- Fiat payments, custody, or mainnet funds.
- Training custom models.

## MVP success measures

- End-to-end demo completes from bounty creation to verdict and payout.
- Every verdict is reproducible from a stored commit SHA and canonical evidence bundle.
- No payout occurs before the challenge window closes.
- Disagreement/outlier cases pause payout and surface a review state.
- A reviewer can understand the result from the GitHub PR without opening the dashboard.

## Key assumptions

- Demo uses a single EVM-compatible testnet and test funds.
- GitHub App installation is limited to repositories controlled by the demo user.
- IPFS pinning and blockchain RPC are available through configured providers.
- Agent scores are advisory; the contract enforces escrow and timing, not AI truth.

## Recommended build order

1. Contracts and local/testnet happy path.
2. Webhook ingress plus GitHub check updates.
3. LangGraph parallel review and canonical evidence schema.
4. IPFS and verdict registry attestation.
5. Dashboard and dispute pause path.
6. Demo hardening, observability, and submission assets.
