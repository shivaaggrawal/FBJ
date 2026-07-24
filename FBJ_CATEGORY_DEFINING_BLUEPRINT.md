# Fair Bounty Judge — Category-Defining Startup Blueprint

**Status:** Strategic redesign brief  
**Date:** 24 July 2026  
**Scope:** Product, market, AI, blockchain, security, business, architecture, UX, fundraising, and long-term moat  
**Implementation note:** This document is intentionally strategy/specification only. It does not prescribe code changes.

---

## 0. Executive verdict

FBJ is startup-worthy, but the current framing is too small.

“AI agents review a GitHub PR and release a crypto bounty” sounds like a feature. It can be copied by a bounty marketplace, a security platform, GitHub, or an AI coding company.

The stronger company is:

> **FBJ is the trust and settlement layer for funded software work.**

It turns an external software contribution into a verifiable lifecycle:

**Intent → Work → Evidence → Independent Review → Human/Community Challenge → Settlement → Reputation**

The crypto bounty is the first payment rail. The durable asset is the **proof graph**: the relationship between a requirement, a commit, tests, review evidence, decision, payment, and future outcome.

### Scores today versus the redesigned opportunity

| Dimension | Current concept | With the redesign and proof |
|---|---:|---:|
| Startup potential | 6.5/10 | 8.8/10 |
| Hackathon strength | 8.5/10 | 9.3/10 |
| Enterprise readiness | 3/10 | 8/10 target |
| Technical innovation | 7.5/10 | 9/10 |
| Market potential | 6.5/10 | 8.5/10 |
| Web3 originality | 7/10 | 8.8/10 |

The main reason for the gap is not technology. It is positioning, trust, distribution, and measurable customer ROI.

---

## 1. Product vision

### The real problem

Funded open-source work fails at four points:

1. **Specification ambiguity:** the maintainer and contributor do not share the same definition of done.
2. **Review bottlenecks:** maintainers must manually inspect quality, security, scope, tests, authorship, and effort.
3. **Settlement distrust:** contributors fear arbitrary rejection; maintainers fear paying for low-quality or malicious work.
4. **No durable reputation:** a good contribution disappears inside a repository and does not compound into portable career capital.

FBJ should not claim to prove that an AI verdict is objectively correct. It should prove that the process was:

- tied to an exact commit;
- evaluated against declared criteria;
- reviewed by independent, versioned evaluators;
- exposed to a defined challenge path;
- settled according to a deterministic policy;
- auditable after the fact.

### The category to own

Call the category **Software Work Assurance** or **Open Work Settlement Infrastructure**.

Avoid leading with “AI code judge.” Judges sound like opaque gatekeepers and invite a direct accuracy comparison with scanners. Lead with:

> **Pay external developers with confidence, without turning every bounty into a manual arbitration process.**

### The first wedge

Do not start as a general bounty marketplace. Start with:

> **GitHub-native settlement and review infrastructure for crypto protocols, developer-tool companies, and open-source foundations running recurring paid issues.**

Best early customers:

- ecosystem and grants teams funding 5–50 issues monthly;
- protocol teams paying contributors for integrations, SDKs, tests, docs, and tooling;
- developer-tool startups with a large external contributor surface;
- foundations that need transparent allocation and reporting;
- hackathon and accelerator programs that need repeatable judging and payout evidence.

The buyer is the maintainer, ecosystem lead, or program manager. The user is the reviewer and contributor. The economic value is reduced review time, faster contributor throughput, lower payout disputes, and a defensible audit trail.

### What FBJ must not become

- A generic task marketplace competing on liquidity.
- A fully autonomous security auditor making safety guarantees.
- A token-first DAO with no repeat customer behavior.
- A reputation score that quietly becomes a permanent blacklist.
- A custodial wallet or opaque AI payout authority.

---

## 2. Market research and competitive strategy

### Competitive map

| Category | Representative products | What they do well | FBJ opportunity |
|---|---|---|---|
| Competitive smart-contract audits | Code4rena, Sherlock | Deep human research, judging, severity calibration, researcher incentives | Own continuous PR-level work assurance after the audit, with evidence and settlement inside GitHub |
| Live security bounty programs | Immunefi, Hats Finance | Large researcher networks, disclosure rules, high-value bug discovery, security-specific workflows | Focus on ordinary funded engineering work, maintenance, integrations, and post-audit change verification |
| Open-source funding | Gitcoin and similar programs | Discovery, grants, ecosystem funding, contributor access | Become the execution, verification, and payout layer underneath existing funding programs |
| Quest and engagement platforms | Layer3 and similar platforms | Discovery, onboarding, incentives, community distribution | Convert quests into verifiable repository work and durable contribution reputation |
| Traditional bounty/work platforms | HackerOne, Bountysource-like workflows, internal procurement tools | Mature intake, tickets, payments, or security operations | Combine GitHub-native work evidence, policy-driven review, programmable escrow, and portable proofs |
| AI code-review tools | Static analyzers, CI copilots, LLM review bots | Fast feedback and developer familiarity | Do not compete on “AI found a bug”; own the decision, evidence, dispute, and settlement layer |

### What the market validates

Code4rena demonstrates that competitive review can attract a large researcher community and that judging, QA, and payout rules are central to trust. Its documented process includes scoped competitions, judging, a QA period, and award calculation. [Code4rena competition process](https://docs.code4rena.com/competitions) and [award mechanics](https://docs.code4rena.com/awarding).

Sherlock demonstrates the value of combining senior review, community coverage, judging, remediation, and fix verification. FBJ should learn from this lifecycle, but apply it to every funded PR rather than only major audit contests. [Sherlock audit contest workflow](https://docs.sherlock.xyz/audits/protocols/how-it-works-for-protocols).

Immunefi demonstrates that security buyers pay for triage, program design, trusted researchers, and operational handling—not only for a smart contract. It also makes clear that continuous programs and human validation matter. [Immunefi bug bounty program](https://immunefi.com/bug-bounty-program/).

Hats Finance demonstrates that non-custodial bounties, on-chain submissions, decentralized security, and community incentives can be productized. That means FBJ needs a sharper wedge than “bounties on-chain.” [Hats Finance overview](https://docs.hats.finance/welcome-to-hats-finance/master).

GitHub Checks are a powerful distribution surface: GitHub Apps can create rich check runs, annotations, and reruns directly on pull requests. FBJ should make the dashboard secondary to the GitHub experience. [GitHub Checks API](https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks).

### Weaknesses FBJ can exploit

1. Large security platforms are optimized for high-severity vulnerabilities, not routine paid engineering work.
2. Audit competitions are episodic; most software risk arrives through subsequent commits.
3. Grant platforms fund work but often do not own technical verification or settlement policy.
4. AI review tools produce advice but rarely provide a mutually trusted decision process.
5. Traditional internal workflows are fragmented across GitHub, tickets, wallets, spreadsheets, and chat.
6. Contributor reputation is usually platform-bound, informal, or based on volume instead of verified outcomes.
7. Most systems do not create a public, independently verifiable proof that a specific commit satisfied a specific funded requirement.

### Blue-ocean opportunities

#### A. Post-audit change assurance

Audits are snapshots. Sell a continuous assurance subscription that evaluates every material PR after the audit, detects changed trust boundaries, and routes only meaningful changes to human reviewers.

#### B. Grant-program operating system

Let a foundation define a program, publish milestones, allocate funds, evaluate submissions, settle payouts, and generate an impact report from the same proof graph.

#### C. Portable contribution credentials

Give developers a privacy-preserving, signed history of verified work: shipped features, severity-calibrated security findings, successful fixes, review quality, and dispute outcomes.

#### D. AI-plus-human review market

AI handles breadth and triage. Staked reviewers handle ambiguous, high-value, or disputed cases. FBJ earns from routing and evidence, not from pretending the AI is infallible.

#### E. Work insurance and outcome financing

Once FBJ has reliable risk data, insurers, protocols, and grant programs can price coverage, reserve capital, or finance milestone work against verified performance.

#### F. Software supply-chain attestations

Turn funded work into procurement-grade evidence: requirement, author, commit, tests, review policy, dependency state, approval, and settlement. This extends beyond crypto.

---

## 3. Product redesign

### The four-layer product

1. **Work layer:** bounty intent, acceptance criteria, repository context, milestones, and contributor submissions.
2. **Intelligence layer:** repository graph, tests, static analysis, AI reviewers, human reviewers, and risk scoring.
3. **Assurance layer:** evidence bundle, policy evaluation, challenge, arbitration, and outcome verification.
4. **Settlement layer:** escrow, payout, refunds, credentials, and on-chain attestations.

### The core object: the Work Passport

Every funded work item should produce a portable Work Passport containing:

- funded requirement and version;
- repository, branch, commit, and changed files;
- test and CI results;
- AI agent outputs, model/version, and confidence;
- human review decisions and conflicts;
- challenge and resolution events;
- payout or refund result;
- post-merge outcome, rollback, or incident linkage;
- privacy controls and redaction status.

The Work Passport is more valuable than a score. It is the durable unit that can be shared, verified, priced, and learned from.

---

## 4. 140 high-impact feature opportunities

The list below is intentionally broad. Do not build all of it. Use it to choose a sharp wedge and a coherent platform sequence.

### MVP — prove the trust loop (15)

1. GitHub App installation with repository allowlisting.
2. Issue-to-bounty creation wizard.
3. Acceptance-criteria builder with examples and edge cases.
4. ERC-20 and native-token escrow on one testnet.
5. PR webhook deduplication by repository, PR, and commit.
6. Pending and completed GitHub Checks.
7. Three typed review agents with independent outputs.
8. Deterministic supervisor policy with configurable thresholds.
9. Exact-commit evidence bundle.
10. IPFS or content-addressed evidence storage.
11. On-chain verdict attestation.
12. Challenge-window countdown.
13. Wallet-signed dispute opening.
14. Human resolution with release/refund outcomes.
15. Public read-only verdict link with verification instructions.

### V2 — make it repeatable (10)

16. Bounty templates by work type.
17. Milestone and partial-payout support.
18. Human approval gates for low-confidence or high-value work.
19. Review retry and failed-job recovery.
20. Repository-level review policies.
21. Contributor onboarding and wallet abstraction.
22. Email, Slack, and Discord notifications.
23. Review history and comparison across commits.
24. Evidence verifier that recomputes the canonical hash.
25. Program dashboard for multiple repositories.

### Enterprise (10)

26. SSO with SAML/OIDC.
27. SCIM provisioning and deprovisioning.
28. RBAC with maintainer, reviewer, finance, auditor, and observer roles.
29. Private cloud or single-tenant deployment.
30. Regional data residency controls.
31. Customer-managed encryption keys.
32. Legal hold, retention, and deletion policies.
33. Procurement export and audit-ready reports.
34. Multi-approval payout policies.
35. SLA, support, and incident-response commitments.

### DAO and protocol operations (10)

36. Treasury-controlled bounty budgets.
37. Safe/multisig payout execution.
38. Proposal-linked bounties.
39. Delegated reviewer roles.
40. Timelocked policy changes.
41. Community challenge periods.
42. On-chain resolution attestations.
43. Treasury analytics by program and outcome.
44. Snapshot/Agora-style governance adapters.
45. DAO-specific disclosure and quorum policies.

### Open source (10)

46. Open evidence schema.
47. Open verifier CLI specification.
48. Public contract interfaces and event schemas.
49. Self-hosted worker mode.
50. Provider-neutral agent interface.
51. Reproducible fixture datasets.
52. Plugin SDK for new review agents.
53. Public benchmark suite.
54. Open policy templates.
55. Transparent incident and postmortem repository.

### AI features (15)

56. Requirements-to-test-case agent.
57. Repository architecture mapper.
58. Dependency and trust-boundary graph.
59. Change-impact analysis.
60. Multi-agent code-quality review.
61. Security reasoning agent with exploit-path narratives.
62. Test-gap detection agent.
63. Regression prediction agent.
64. License and provenance agent.
65. Contributor-collusion and plagiarism detection.
66. Prompt-injection and malicious-diff defense agent.
67. Evidence-grounded explanation generator.
68. Reviewer-assist copilot for disputes.
69. Patch suggestion agent with human approval.
70. Post-merge outcome-learning agent.

### Developer experience (10)

71. Walletless contributor onboarding.
72. GitHub-native bounty discovery.
73. One-click “I intend to work on this” flow.
74. Local review preview before submission.
75. Pre-submission acceptance-criteria checklist.
76. Automatic test and lint result import.
77. Review comments grouped by severity and confidence.
78. “Explain this decision” interaction.
79. “Request human review” action.
80. Contributor payout and tax-status center.

### Analytics (10)

81. Time-to-first-contributor metric.
82. Time-to-verdict metric.
83. Payout and refund rate.
84. Dispute rate by repository and policy.
85. Agent precision/recall against human outcomes.
86. Review cost per bounty.
87. Maintainer hours saved.
88. Contributor conversion funnel.
89. Post-merge defect and rollback rate.
90. Program ROI and capital efficiency.

### Security (10)

91. Secret redaction before every AI call.
92. Diff-size and archive-bomb limits.
93. Sandboxed code execution.
94. Egress-controlled analysis workers.
95. Immutable audit logs.
96. Transaction simulation before payout.
97. Relayer spending caps.
98. Contract pause and guardian controls.
99. Chain reorganization reconciliation.
100. Automated evidence-integrity verification.

### Governance and policy (10)

101. Versioned review policies.
102. Policy dry-run mode.
103. Threshold simulation on historical reviews.
104. Conflict-of-interest declarations.
105. Reviewer independence rules.
106. Appeal and escalation ladders.
107. Policy change timelocks.
108. Jurisdiction and payout restrictions.
109. Audit trail for every decision change.
110. Human override with mandatory reason.

### Community and reputation (10)

111. Verified contributor profiles.
112. Portable Work Passport credentials.
113. Reviewer accuracy leaderboard.
114. Maintainer fairness score.
115. Challenge quality reputation.
116. Community mentorship tracks.
117. Good-first-bounty programs.
118. Achievement badges for shipped work.
119. Public ecosystem impact reports.
120. Community moderation and appeals council.

### Marketplace (10)

121. Bounty discovery marketplace.
122. Specialist reviewer marketplace.
123. Human arbitration marketplace.
124. Review-agent marketplace.
125. Escrow and payout provider marketplace.
126. Insurance and coverage marketplace.
127. Grant-program distribution marketplace.
128. Maintainer services marketplace.
129. Curated high-trust contributor pools.
130. Program sponsorship and matching pools.

### Integrations (10)

131. GitHub App, Checks, Issues, Projects, and Discussions.
132. GitLab and Bitbucket adapters.
133. Safe multisig.
134. WalletConnect and account abstraction wallets.
135. Slack, Discord, and Telegram notifications.
136. Linear, Jira, and Notion synchronization.
137. CI providers and artifact stores.
138. IPFS, Arweave, S3, and customer storage.
139. Block explorers and chain indexers.
140. SIEM, PagerDuty, and procurement systems.

---

## 5. AI strategy: make intelligence the moat, not the gimmick

### The wrong AI story

“Three LLMs score a PR” is not defensible. Models change, prompts leak, and competitors can call the same providers.

### The right AI story

FBJ should build an **evidence-grounded software work intelligence system** that learns from:

- requirements;
- repository architecture;
- code and dependency graphs;
- test behavior;
- historical review decisions;
- challenges and human overrides;
- post-merge defects;
- exploit and incident outcomes;
- contributor and maintainer behavior.

### Agent system

#### Planning agents

- Convert vague issue text into testable acceptance criteria.
- Identify missing requirements and ask clarifying questions.
- Create a review plan based on changed trust boundaries.
- Select the right agents and human specialists.

#### Analysis agents

- Build a repository and dependency graph.
- Compare code semantics across commits.
- Trace data flow, privilege flow, and asset flow.
- Run static analysis, tests, fuzzing, symbolic execution, and dependency checks.
- Search historical incidents and similar patches.

#### Decision agents

- Normalize findings into a shared ontology.
- Estimate severity, confidence, novelty, and exploitability separately.
- Detect agent disagreement and correlated hallucinations.
- Recommend eligible, conditional, or human-review outcomes.

#### Interaction agents

- Explain a verdict to a contributor without humiliation.
- Coach contributors before submission.
- Help maintainers improve criteria.
- Facilitate structured negotiation during a dispute.
- Generate a decision memo for a human judge.

#### Learning agents

- Compare predicted risk with post-merge outcomes.
- Detect systematic bias against languages, contributors, or repository types.
- Calibrate scores per domain.
- Identify which agent or tool actually added signal.

### AI safety principles

1. Never let an LLM directly authorize a valuable payout.
2. Separate analysis, recommendation, and authorization.
3. Require citations to files, lines, tests, traces, or evidence objects.
4. Preserve raw outputs and normalized outputs separately.
5. Version model, prompt, tools, policy, and repository snapshot.
6. Treat code, issue text, comments, and test output as untrusted input.
7. Use confidence intervals and abstention, not only a score.
8. Train on outcomes, not merely human preferences.
9. Make every model decision reversible during the challenge window.
10. Publish benchmark results, including failures and false positives.

### The proprietary AI moat

The moat is the **outcome dataset**, not the prompt:

`requirement → change → review → challenge → settlement → post-merge result`

Over time FBJ can learn which evidence predicts successful work, which review findings are useful, which policies reduce disputes, and which contributors consistently ship safe changes. Competitors can copy agents; they cannot instantly copy a decade of outcome-linked work evidence.

---

## 6. Blockchain strategy: use the chain only where it adds trust

### High-value on-chain primitives

1. Escrow and settlement finality.
2. Immutable evidence commitments.
3. Time-bounded challenge windows.
4. Portable attestations of work and review outcomes.
5. Staked reviewer commitments.
6. Slashing for demonstrably dishonest or conflicted review behavior.
7. Treasury and grant transparency.
8. Cross-organization program composability.

### Low-value blockchain ideas to avoid early

- A speculative FBJ token.
- On-chain storage of code, private diffs, or personal data.
- Token voting on every ordinary review.
- Making contributors pay gas before they can submit work.
- A single anonymous AI signer controlling payouts.

### Reputation architecture

Use a layered reputation model rather than one score:

- **Contributor reliability:** accepted work, rework, rollback, and dispute outcomes.
- **Reviewer accuracy:** confirmed findings, false positives, calibration, and appeal reversals.
- **Maintainer fairness:** payout behavior, response time, and upheld decisions.
- **Program quality:** clarity of criteria, dispute rate, and contributor retention.

Publish only the minimum necessary. Support pseudonymous credentials, selective disclosure, expiry, correction, and the right to contest an outcome.

### Staking and slashing

Introduce staking only for human reviewers or arbitration providers after there is meaningful volume.

- Stake signals seriousness and funds dispute costs.
- Slashing requires a clear policy, evidence, an appeal path, and a bounded penalty.
- Never slash a reviewer merely because an opinion lost a majority.
- Slash only for provable fraud, collusion, fabricated evidence, undisclosed conflict, or repeated reckless behavior.
- Use a safety council or multi-party appeal for high-value cases.

### Optimistic settlement

The default should be optimistic:

1. A policy-approved verdict is published.
2. A challenge window opens.
3. Anyone with standing can challenge with evidence.
4. No challenge means automatic settlement.
5. A challenge routes the case to human or community arbitration.

### Zero-knowledge opportunities

Use ZK selectively for:

- proving a reviewer passed a qualification threshold without exposing identity;
- proving a contribution met a test predicate without publishing private code;
- proving a program followed a policy without exposing all customer data;
- proving eligibility or reputation bands without doxxing a contributor.

Do not use ZK just to say “we use ZK.” The proof must solve privacy, procurement, or conflict-of-interest problems.

### Account abstraction and payments

Use smart accounts for organization treasuries, session keys, batched approvals, gas sponsorship, and spending limits. ERC-4337 smart accounts support programmable authentication, authorization, fee payment, nonce management, and execution. [ERC-4337 smart accounts](https://docs.erc4337.io/smart-accounts/index.html).

### Cross-chain design

Keep the evidence and policy identifiers chain-neutral. Use a payout adapter per chain. Anchor the same Work Passport hash to one canonical registry and mirror settlement events through verified bridges or message protocols.

Never make cross-chain payout state depend on an unverified event from a single bridge.

---

## 7. Enterprise-grade security model

FBJ is a financial workflow, a code-analysis system, and a reputation system. It must defend all three.

### Threats and controls

| Threat | Example attack | Required control |
|---|---|---|
| Fake GitHub webhook | Replay or forge a PR event | HMAC verification, delivery-id deduplication, timestamp/replay limits |
| Repository confusion | Bounty maps to the wrong repository | Installation ownership, canonical repository IDs, allowlists |
| Commit substitution | Verdict for one commit pays another | Bind every artifact to immutable commit SHA and tree hash |
| Prompt injection | Malicious code comments instruct the agent | Treat all repository text as data; isolated system instructions; output validation |
| Secret exfiltration | Diff contains credentials | Secret scanning, redaction, egress policy, provider controls |
| Diff bomb | Huge archive consumes workers | Size, file-count, nesting, decompression, and CPU limits |
| Tool escape | Analysis tool runs attacker-controlled code | Sandboxed workers, no secrets, no privileged network, ephemeral environments |
| Agent collusion | Same correlated model produces false consensus | Provider/model diversity, independent prompts, blind aggregation, human escalation |
| Score gaming | Contributor optimizes for the score | Hidden adversarial tests, policy diversity, post-merge outcomes, novelty checks |
| Sybil reviewers | Many identities influence decisions | Identity tiers, stake, history, rate limits, graph-based anomaly detection |
| Maintainer abuse | Rejects valid work to keep funds | Escrow, response SLA, challenge rights, fairness reputation, arbitration |
| Contributor fraud | Plagiarized or malicious contribution | Provenance analysis, dependency checks, sandbox tests, disclosure policy |
| Relayer compromise | Attacker releases funds | Narrow roles, spending caps, multisig, timelocks, pause guardian, key rotation |
| Contract bug | Double payout or locked funds | Minimal contracts, formal invariants, fuzzing, audit, bug bounty, pause path |
| Oracle/indexer drift | Database says paid when chain says pending | Chain as source of truth, event reconciliation, finality depth, reorg handling |
| Evidence tampering | IPFS bytes differ from attested bytes | Canonical serialization, hash-before-pin, fetch-and-verify, content-addressed storage |
| Privacy leak | Private code becomes public | Private storage adapter, encryption, retention policy, redaction report |
| Identity theft | Wallet or GitHub account takeover | SIWE nonce binding, GitHub OAuth/App identity, session rotation, MFA/SSO |
| Dispute griefing | Cheap challenges halt every payout | Challenger bond, rate limits, evidence minimums, capped challenge time |
| Governance capture | Whales change payout policy | Timelocks, quorum, delegated roles, emergency guardian, proposal simulation |

### Security standards and operating posture

Align the security program with NIST SSDF practices and maintain a clear secure-development evidence trail. [NIST SSDF](https://csrc.nist.gov/projects/ssdf).

Required before production funds:

- threat model per service and contract;
- external smart-contract audit;
- property-based and invariant testing;
- independent key-management review;
- least-privilege GitHub App permissions;
- signed builds and dependency provenance;
- continuous secret scanning;
- vulnerability disclosure policy;
- incident-response runbooks;
- disaster-recovery and chain-reconciliation drills;
- penetration test for webhook, wallet, dispute, and evidence paths;
- security review of AI data retention and provider access.

Use role-based permissions and timelocked administrative actions. OpenZeppelin documents role-based access, managed permissions, guardians, and execution delays as important controls for complex contract systems. [OpenZeppelin AccessControl and AccessManager](https://docs.openzeppelin.com/contracts/5.x/access-control).

---

## 8. Business model

### Revenue options

| Model | Buyer | Pricing logic | Strategic value |
|---|---|---|---|
| Free/testnet | Developers and small projects | Free with limits | Distribution and trust |
| SaaS team plan | Maintainers and startups | Monthly fee by repositories, reviewers, or work items | Predictable recurring revenue |
| Settlement fee | Programs and protocols | 1–2% of successfully settled bounty value | Aligns price with customer value |
| Enterprise platform | Large organizations | Annual contract plus usage | High ACV, security and support revenue |
| Managed triage | Protocols and foundations | Fee per review or monthly capacity | Human quality layer |
| Premium AI | Teams with private code | Per-repository or per-analysis | Monetizes compute and private deployment |
| Reviewer marketplace | Reviewers and buyers | Take rate on human review/arbitration | Network effect |
| API/embedded | Wallets, grant platforms, CI vendors | Usage-based API fee | Becomes infrastructure |
| Analytics | Foundations and ecosystem teams | Subscription by program and data depth | Outcome intelligence |
| Insurance/coverage | Protocols, insurers, treasuries | Underwriting or referral fee | New financial product after data maturity |
| White label | Chains, accelerators, enterprise programs | Setup fee plus annual license | Distribution through institutions |

### Recommended commercial sequence

1. Start with free fixture/testnet and a paid pilot for program operators.
2. Charge for managed review, private data controls, analytics, and support before charging meaningful settlement fees.
3. Offer an enterprise annual contract once security and reliability are credible.
4. Add marketplace take rates only after supply and demand are both real.
5. Delay a token until the protocol has organic activity that a token would improve.

### Unit economics to prove

- gross margin per review;
- cost of AI and human review;
- average bounty value and settlement fee;
- customer payback period;
- repeat bounty rate;
- dispute handling cost;
- revenue retained after refunds and support;
- percentage of work programs that expand from one repository to many.

---

## 9. Virality and distribution

### The GitHub loop

1. A maintainer creates a bounty.
2. The bounty produces a visible GitHub Check and issue label.
3. A contributor submits a PR.
4. The PR contains a shareable review result and proof link.
5. The contributor shares the Work Passport.
6. New maintainers discover FBJ through the repository and install the App.

### Growth loops

- Public bounty pages optimized for search.
- Contributor profiles with permissioned verified achievements.
- Shareable “review proof” cards for shipped work.
- Ecosystem leaderboards based on verified outcomes, not raw volume.
- Referral credits for maintainers and contributors.
- Hackathon starter kits with instant testnet escrow.
- Open benchmark reports comparing AI review signal to human outcomes.
- Public postmortems showing how a challenge prevented a bad payout.
- Program templates that foundations can copy.
- “Powered by FBJ” GitHub Check branding with opt-out for enterprise customers.

### Avoid harmful gamification

Do not reward spam, raw submission count, maximum activity, or public shaming. Reputation should be earned through accepted outcomes, useful challenges, review calibration, and fair behavior.

---

## 10. Production architecture

### Logical services

1. **Edge/API gateway:** authentication, rate limits, request IDs, tenant routing.
2. **Identity service:** GitHub App installation, SIWE, SSO, roles, sessions.
3. **Bounty service:** requirements, budgets, policies, milestones, state machine.
4. **Webhook service:** signature verification, replay defense, durable ingestion.
5. **Review orchestrator:** schedules plans, agents, tools, retries, and human gates.
6. **Analysis workers:** isolated static analysis, tests, fuzzing, symbolic execution, and LLM calls.
7. **Evidence service:** canonicalization, encryption, hashing, storage, and verification.
8. **Settlement service:** chain adapters, transaction simulation, relayers, confirmations.
9. **Dispute service:** challenge bonds, evidence, arbitration routing, outcomes.
10. **Reputation service:** credentials, outcome updates, privacy controls, attestations.
11. **Notification service:** GitHub, email, Slack, Discord, PagerDuty.
12. **Analytics service:** event warehouse, metrics, cohort analysis, and exports.

### Event-driven flow

GitHub event → verified event log → review-created event → plan-created event → parallel analysis events → evidence-created event → policy-evaluated event → verdict-published event → challenge-open event → settlement-authorized event → payout-confirmed event → reputation-updated event.

Every event should have:

- tenant ID;
- correlation/request ID;
- work item ID;
- repository and commit identity;
- event version;
- producer and timestamp;
- idempotency key;
- previous state and next state;
- privacy classification.

### Recommended infrastructure

- PostgreSQL for transactional operational state.
- Object storage for encrypted evidence and artifacts.
- Content-addressed public evidence only when the customer permits it.
- Redis for short-lived caching and rate limits.
- Durable queue such as Kafka, NATS JetStream, SQS, or equivalent.
- Workflow engine such as Temporal for retries, timers, and long-running disputes.
- Vector store for repository and historical evidence retrieval, never as the source of truth.
- Columnar warehouse for product and model analytics.
- OpenTelemetry for traces, logs, and metrics.
- Kubernetes or managed container platform only when workload and team maturity justify it.

### Scaling principles

- Separate webhook acknowledgement from review execution.
- Use per-tenant concurrency budgets.
- Cache repository snapshots by commit.
- Deduplicate identical analyses.
- Route high-risk work to deeper tools.
- Keep a provider abstraction for models and chains.
- Store all policy versions with the result.
- Make every worker idempotent and retryable.
- Design chain adapters around finality and reorg recovery.
- Begin as a modular monolith with durable workers; split services only at real scaling boundaries.

### Observability

Track:

- webhook acceptance latency;
- review queue age;
- time per agent and tool;
- model failure and abstention rates;
- false-positive and appeal rates;
- evidence verification failures;
- transaction pending duration;
- chain reorg/reconciliation events;
- dispute volume and SLA;
- payout failure rate;
- AI cost per accepted work item;
- customer-visible incident rate.

---

## 11. UX/UI redesign

### Maintainer journey

1. Install App and choose repository.
2. Create bounty from an issue or template.
3. Define acceptance criteria using examples and non-goals.
4. Choose token, budget, challenge period, and policy.
5. Fund through Safe or smart account.
6. See work status inside GitHub and dashboard.
7. Receive evidence-backed verdict.
8. Approve, challenge, request changes, or escalate.
9. Release payout automatically or manually.
10. Receive a program and contributor impact report.

### Developer journey

1. Discover bounty in GitHub.
2. Read clear criteria, reward, scope, and challenge policy.
3. Claim intent without committing to a deadline that creates friction.
4. Get a local preflight checklist.
5. Submit PR.
6. See agent feedback and ask for explanation.
7. Respond to findings or request human review.
8. Receive payout and portable Work Passport.

### Reviewer journey

1. See only cases routed by policy and expertise.
2. Compare evidence, agent outputs, tests, and criteria.
3. Declare conflict of interest.
4. Make a structured decision with severity and confidence.
5. Sign the decision and expose rationale.
6. Earn reputation based on later outcome quality.

### Judge/arbitrator journey

1. Receive a challenged case with full timeline.
2. Review both parties’ evidence without hidden edits.
3. Inspect agent disagreement and policy version.
4. Request additional tests or a limited reproduction.
5. Publish a reasoned decision.
6. Trigger settlement and update credentials.

### Enterprise journey

1. Connect SSO, repositories, policies, treasury, and data region.
2. Define roles and approval limits.
3. Import existing bounty and grant programs.
4. Run in shadow mode beside existing review.
5. Compare FBJ recommendations with human outcomes.
6. Enable automated settlement only for approved policy bands.
7. Export procurement, compliance, and impact evidence.

### DAO journey

1. Connect Safe and governance.
2. Create a program budget and policy.
3. Delegate reviewer and resolver roles.
4. Publish transparent bounty terms.
5. Route disputes to a defined quorum/arbitration process.
6. Publish treasury and outcome reports.

### Design principles

- GitHub is the primary surface; the dashboard is the control plane.
- Explain decisions before displaying scores.
- Show uncertainty and dissent, not only a green/red verdict.
- Keep money, evidence, and action status visible together.
- Never hide a human override.
- Make privacy level explicit for every artifact.
- Keep contributor experience wallet-optional until payout.

---

## 12. Enterprise buying requirements

Large companies and serious protocols will expect:

- SSO, SCIM, RBAC, audit logs, and separation of duties.
- Private repository support and clear data retention.
- No training on customer code without explicit opt-in.
- Dedicated or customer-managed model routing.
- Vendor security questionnaire support.
- SOC 2 roadmap and penetration testing.
- Regional hosting and deletion guarantees.
- Reliable SLAs, support, incident communication, and status page.
- Reproducible decisions and exportable evidence.
- Customer-owned wallets or Safe-controlled treasury.
- Spending caps, transaction simulation, timelocks, and emergency pause.
- Stable APIs, webhooks, SDKs, and versioning.
- Legal terms for AI limitations, arbitration, payouts, and data processing.
- Accessibility and localization.
- Procurement-friendly fiat billing even if the payout rail is crypto.
- A shadow mode that never blocks merge or pays automatically until trusted.

The enterprise product should be able to work with no public blockchain at all for internal work, then use blockchain selectively for external settlement and attestations.

---

## 13. Roadmap

### First 3 months — prove activation and trust

- One GitHub App and one chain.
- One clear ICP and 3–5 design partners.
- Bounty templates and criteria assistant.
- GitHub Checks as the primary UX.
- Human approval for every payout.
- Public or permissioned Work Passport.
- Evidence verifier and dispute path.
- Shadow-mode comparison against human review.
- Measure time-to-verdict, dispute rate, payout completion, and maintainer hours saved.

### 6 months — become a program operating system

- Multiple repositories per organization.
- Milestones and partial payout.
- Durable workflow engine and retry/reconciliation.
- Human reviewer network.
- Notifications and program analytics.
- Safe/smart-account treasury integration.
- Contributor profiles and privacy-preserving credentials.
- Three design-partner case studies with quantified ROI.

### 1 year — establish the category

- Multi-chain payout adapters.
- Enterprise controls and private deployment option.
- Post-audit continuous assurance product.
- API and embedded mode for grant programs.
- Outcome-trained risk models.
- Human arbitration marketplace.
- Open Work Passport and verifier standard.
- Revenue from SaaS, managed review, and APIs.

### 3 years — become the network

- Millions in verified external software work.
- Large contributor and reviewer reputation graph.
- Programmatic insurance or coverage products.
- Cross-ecosystem grant and bounty routing.
- Institutional customers and procurement integrations.
- Standardized proof of software work used by wallets, funds, and ecosystems.

### 5 years — the ambitious outcome

FBJ becomes the neutral settlement and assurance network for external software work across open source, Web3, AI tooling, security research, and developer ecosystems.

The platform is not merely paying bounties. It is pricing trust in software work.

---

## 14. Fundraising analysis

### Would top investors invest?

Potentially, but not for the current demo alone.

#### YC

YC may like the GitHub distribution, clear workflow, and fast design-partner feedback. They will ask: who urgently needs this, how often, and why can’t GitHub or an existing bounty platform add it?

Fix: show repeated usage, a narrow ICP, and a measurable reduction in maintainer review time or dispute cost.

#### a16z Crypto / Coinbase Ventures / Paradigm

They may like programmable escrow, crypto-native contribution markets, attestations, and network effects. They will question whether the market is large enough and whether the company is a SaaS tool or a protocol.

Fix: lead with a software-work assurance market, prove SaaS revenue first, and show why on-chain settlement and reputation create unique distribution and composability.

#### Sequoia-style software investors

They will favor developer infrastructure and enterprise workflow but may discount crypto complexity.

Fix: make the core product useful with fiat or internal settlement, while blockchain adds external trust and programmable payout rather than being mandatory.

### Investor objections to answer

1. **“AI review is commoditized.”**
   - Answer with outcome data, evidence graph, human arbitration, and settlement network effects.
2. **“Why not GitHub Actions?”**
   - Actions test code; FBJ coordinates external work, money, policy, dispute, and portable proof.
3. **“Why not Immunefi or Code4rena?”**
   - They are excellent at high-value security programs; FBJ owns recurring engineering work and post-audit change assurance.
4. **“Crypto limits the market.”**
   - Use a chain-neutral API and support fiat/internal mode; make crypto the strongest trust and settlement rail, not the only onboarding gate.
5. **“Who is liable for a bad verdict?”**
   - Advisory AI, explicit policy, human gates, insurance/coverage partners, audit logs, and no autonomous high-value payout.
6. **“Where is the liquidity?”**
   - Start with existing program budgets and repositories; marketplace liquidity is a later effect, not the first assumption.
7. **“Why will contributors switch?”**
   - Because the Work Passport compounds into portable, verified opportunity and payment history.

### What fundraising proof should look like

- 3–5 design partners.
- 50+ real work items.
- 80%+ reviewer agreement on ordinary cases.
- Documented false-positive and appeal behavior.
- Meaningful repeat usage.
- At least one paid contract.
- One case where evidence prevented a bad payout or resolved a dispute fairly.
- Clear gross margin after AI and human review costs.

---

## 15. Moat design

### Moat 1: outcome-linked proof graph

Most products store reviews. FBJ should link reviews to later outcomes: merged, reverted, exploited, maintained, disputed, and paid. This creates a proprietary label set for software work quality.

### Moat 2: policy network effects

As more programs use FBJ policies, the system learns which acceptance criteria and review policies produce fewer disputes and better outcomes.

### Moat 3: portable reputation

Contributors and reviewers carry verified credentials across programs. They bring the network to every new repository.

### Moat 4: human-plus-AI arbitration network

The best hard cases become training data and reviewer reputation events. This creates a quality flywheel that a generic AI reviewer cannot easily reproduce.

### Moat 5: embedded settlement

Once treasury, payout, dispute, and reporting workflows run through FBJ, switching costs become operational rather than merely technical.

### Moat 6: standard ownership

Open the evidence schema and verifier, but make the outcome network, policy intelligence, routing, and enterprise operations the proprietary layer. The ecosystem expands FBJ’s distribution without giving away the business.

### Moat flywheel

More programs → more work items → more outcomes → better policies and AI calibration → fewer disputes and lower review cost → more trust → more programs.

---

## 16. Missing assumptions and bold redesigns

### Assumption: every PR should be judged the same way

False. A docs PR, a UI change, a smart-contract upgrade, and a dependency update need different policies and evidence. Make the review plan adaptive.

### Assumption: the maintainer is always the legitimate judge

False. A maintainer can be biased, unavailable, compromised, or financially conflicted. Build explicit escalation and fairness signals.

### Assumption: a public IPFS bundle is always good

False. Private repositories, secrets, regulated data, and exploit details require encrypted customer-controlled storage and selective disclosure.

### Assumption: score is the best output

False. A score hides uncertainty. The output should be a decision recommendation with evidence, dissent, confidence, and next actions.

### Assumption: a challenge window alone creates fairness

False. A challenge is only useful if the challenger has standing, evidence access, a fair venue, and a credible resolution path.

### Assumption: token incentives create community

False. Useful work, fair rules, and repeat opportunity create community. Add tokens only when they solve a real coordination or security problem.

### Bold idea 1: Work Passport becomes a hiring primitive

Companies can recruit from verified shipped work rather than résumé claims. Contributors can selectively prove impact without exposing private code.

### Bold idea 2: Continuous assurance after every audit

FBJ becomes the monitoring layer that knows what changed after an audit and automatically routes risk-heavy changes for review.

### Bold idea 3: Outcome insurance

Programs can purchase coverage for mis-settled or malicious work. FBJ supplies evidence and risk signals; a regulated partner underwrites the policy.

### Bold idea 4: Challenge markets

Qualified reviewers can stake against a verdict and earn if their challenge is upheld. This creates a market for attention, but requires strong anti-griefing and legal design.

### Bold idea 5: Agent licensing marketplace

Specialist agents—Solidity, Rust, cryptography, frontend accessibility, dependency risk—can publish evaluation modules with benchmarked accuracy and usage-based revenue.

### Bold idea 6: Grant OS, not bounty board

Foundations fund outcomes, not tasks. FBJ can model programs, milestones, deliverables, outcomes, and downstream impact in one evidence graph.

---

## 17. Non-negotiable product principles

1. Money never moves because one LLM said “pass.”
2. Every decision is tied to immutable work identity and a policy version.
3. AI may recommend; humans or deterministic policy authorize.
4. Every participant can see the rules before committing work.
5. Every participant has a meaningful appeal path.
6. Privacy is a first-class product setting.
7. Reputation is portable, explainable, and contestable.
8. The chain is used for trust, settlement, and coordination—not decoration.
9. GitHub is the distribution surface.
10. The company measures outcomes, not feature count.

## Final startup thesis

FBJ should not try to become the next generic bounty platform. It should become the **neutral assurance and settlement layer for software work that crosses organizational boundaries**.

The winning sequence is:

**GitHub App → recurring paid work → evidence-backed review → fair challenge → programmable settlement → portable reputation → outcome intelligence → network.**

That is a category-defining company. The crypto bounty is only the first wedge.
