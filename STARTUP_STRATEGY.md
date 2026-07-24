# Fair Bounty Judge — startup enhancement brief

## Positioning

Fair Bounty Judge should be sold as **review infrastructure for funded open-source work**, not as another crypto bounty board.

> GitHub-native, evidence-backed payout protection for teams that pay external contributors.

The product already has the difficult technical primitives: an escrow lifecycle, GitHub webhook ingress, parallel review agents, deterministic evidence, IPFS pinning, on-chain attestation, and a challenge/dispute path. The startup opportunity is to package these primitives into a product that a maintainer can trust in under five minutes.

## What the market tells us

- Gitcoin describes bounties as funded tasks that contributors complete for a reward. That validates demand for paid open-source work, but also means generic bounty discovery is a crowded positioning.
- Gitcoin's own history shows that the category is broader than a contract: discovery, contributor trust, and program management matter as much as payment.
- GitHub's Checks API supports GitHub Apps that report directly on pull requests. This is the best distribution channel because contributors already work inside GitHub.

Sources: [Gitcoin Bounties](https://gitcoin.co/mechanisms/bounties), [Gitcoin About](https://gitcoin.co/about), [GitHub Checks REST API](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks).

## Best first customer

Start with crypto protocols, developer-tool startups, and open-source foundations that run 5–50 paid issues per month. They have enough review volume to feel the pain, but are still able to install a GitHub App and adopt a new workflow quickly.

The buyer is the maintainer or ecosystem lead. The user is the reviewer and contributor. The economic buyer wants fewer wasted payouts and faster review; the contributor wants a verdict that is explainable and challengeable.

## Product enhancements by priority

### P0 — make the demo production-shaped

1. Guided onboarding: connect GitHub, select a repository, create the first bounty, and show the exact next action.
2. Dashboard KPIs: funded amount, active reviews, completed payouts, and disputes requiring action.
3. Trust layer: show commit SHA, agent agreement, evidence hash/CID, attestation transaction, and challenge countdown in one place.
4. Contributor view: a public, read-only verdict page or signed link that works without a wallet.
5. Failure states: retry review, stale webhook, missing recipient, failed attestation, and chain confirmation timeout must be actionable.
6. Safe rendering and server-side authorization before allowing any production deployment.

### P1 — turn it into a repeatable workflow

1. Bounty templates for security fixes, documentation, integrations, and good-first-issues.
2. Approval policy per repository: minimum score, required agents, human approval, and maximum reward.
3. Review history and analytics: time to verdict, payout rate, dispute rate, agent disagreement, and review cost.
4. GitHub App installation flow and repository-level configuration instead of manually pasting URLs.
5. Email/Slack notifications for pending reviews, challenge expiry, disputes, and failed jobs.
6. Contributor reputation based on completed, non-disputed work; keep it explainable and never make it the only eligibility signal.

### P2 — scale the business

1. Team workspaces, roles, audit logs, and approval policies.
2. Multi-chain and stablecoin support behind one payout abstraction.
3. Human reviewer marketplace for flagged or high-value work.
4. API/webhooks for ecosystem programs and grant operators.
5. Enterprise retention controls, redaction reports, and private-repository data policies.

## Business model to test

- Free: one repository, fixture/testnet mode, and limited monthly reviews.
- Team: monthly platform fee plus 1–2% of successfully released bounty value.
- Program: negotiated fee for foundations or ecosystems with reviewer SLAs and analytics.

Do not launch a token before there is recurring usage. The core value is trust and workflow reliability, not speculation.

## Metrics that prove product-market pull

- Time from bounty creation to first valid PR.
- Median time from PR webhook to verdict.
- Percentage of verdicts accepted without dispute.
- Percentage of flagged verdicts resolved within an SLA.
- Payout completion rate and failed-transaction rate.
- Maintainer hours saved per bounty.
- Repeat bounty rate per repository.

The strongest early proof is three design partners running real testnet bounties, with before/after review time and a documented dispute case.

## Risks to close before real money

- AI output is advisory; high-value or low-confidence verdicts should require human approval.
- The API must authenticate maintainer/reviewer actions and enforce repository installation ownership.
- All webhook and worker paths need idempotency, retries, a durable queue, and observable state transitions.
- IPFS evidence should exclude secrets and private code unless the customer explicitly accepts that retention model.
- Contracts need an independent review before mainnet or production custody. The MVP should stay on testnet and use a dedicated relayer with narrowly scoped roles.

## Recommended 30-day execution plan

### Week 1 — activation

Ship the guided dashboard, KPI cards, status filters, clear fixture-mode labeling, and a shareable evidence view. Interview 5 maintainers while they use the flow.

### Week 2 — trust

Add review retry/failure recovery, challenge countdowns, a public verdict link, and a verification endpoint that recomputes the evidence hash from the exact bytes.

### Week 3 — operations

Move background reviews to a durable queue, add structured logs and metrics, enforce auth/roles, and test webhook replay plus chain reconciliation under failure.

### Week 4 — pilot

Run three design-partner bounties, measure the metrics above, record one happy-path and one disputed-path demo, and decide whether the wedge is protocol teams, developer tools, or foundations.

## Product north star

Every funded pull request should have a fast verdict that a maintainer can act on, a contributor can challenge, and an auditor can independently verify.
