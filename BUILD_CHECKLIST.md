# Fair Bounty Judge — Build Checklist

## Current baseline

The blockchain implementation in `Blockchain/` is deployed on Polygon Amoy and verified locally: `npm.cmd test` passes **10/10 tests**. It uses ERC-20 rewards on Polygon Amoy, not native-token deposits. The API, dashboard, GitHub App, MongoDB, Pinata, and Groq configuration are integrated. The remaining work is primarily real external end-to-end proof and submission material.

## 0. Decisions to lock before wiring components

- [x] Select the AI model/provider and record model names and prompt version. Runtime is configured for Groq (`llama-3.3-70b-versatile`).
- [x] Select the IPFS pinning provider and create an API credential (Pinata).
- [x] Select MongoDB and configure the development database.
- [x] Choose the GitHub repository used for the live demo (`shivaaggrawal/Image-Editor`).
- [x] Confirm the test ERC-20 reward token deployed on Polygon Amoy.
- [x] Confirm the relayer wallet and dispute-resolver wallet.
- [x] Decide the demo score policy: chain threshold is 7,000 bps (70%).
- [x] Decide the demo challenge period: deployment metadata uses three days.

## 1. Blockchain — already implemented

- [x] ERC-20 `BountyEscrow` with exact-balance checking and fee-on-transfer token rejection.
- [x] Per-bounty token, amount, maintainer, recipient, expiry, and lifecycle state tracking.
- [x] `VerdictRegistry` for evidence hash, IPFS CID, score, recipient, and challenge deadline.
- [x] Role-gated relayer submission; the AI workflow has no direct on-chain authority.
- [x] `DisputeManager` that lets maintainer or recipient challenge and an adjudicator resolve.
- [x] Pause controls, access control, safe token transfers, and reentrancy protections.
- [x] Hardhat deployment and transaction scripts.
- [x] Contract tests covering happy path, timing, authorization, token behavior, disputes, pause, and invalid dependencies.

## 2. Blockchain — remaining integration work

- [x] Create the repository-root `.env` locally from `.env.example`; never commit it. This single file is used by both the API and Hardhat.
- [x] Fund the deployment and service wallets with Amoy POL for deployment and demos.
- [x] Deploy a test ERC-20 reward token on Amoy.
- [x] Set RPC, deployment, reward-token, relayer, resolver, and deployed-contract configuration.
- [x] Deploy the contracts to Amoy and save the chain ID and deployed addresses in local configuration.
- [ ] Verify each deployed contract on the selected explorer if time permits.
- [x] Add a read-only role audit command: `npm.cmd run roles:check:amoy` verifies the deployed dependency graph and all required roles.
- [x] Add an application contract configuration object: `chainId`, `bountyEscrow`, `verdictRegistry`, `disputeManager`, `rewardToken`.
- [ ] Generate/use ABIs and typed contract clients in the backend and dashboard.
- [x] Implement backend calls to existing functions:
  - [x] Prepare `createBounty(bytes32,address,uint128,uint64)` plus ERC-20 approval for a connected wallet, then verify its confirmed transaction before registration.
  - [x] `submitVerdict(bytes32,bytes32,string,address,uint16)` from the relayer service.
  - [x] `releaseBounty(bytes32)` after the challenge deadline.
  - [x] Prepare `openDispute(bytes32,string)` from the connected maintainer/recipient wallet with pinned, hash-verified evidence.
  - [x] Prepare `resolveDispute(bytes32,Resolution)` from the designated resolver wallet.
- [x] Poll and persist `BountyCreated`, `VerdictSubmitted`, `DisputeOpened`, `BountyPaid`, `BountyRefunded`, and resolution events with replay-safe cursors.
- [ ] Set `CHAIN_EVENT_START_BLOCK` to the Amoy deployment block before the first real demo, so historical events can be replayed after restarts.
- [ ] Add one Amoy end-to-end smoke test using a small test-token bounty.
- [x] Align `SPEC.md` terminology and contract signatures with this ERC-20 implementation.

## 3. Backend foundation

- [x] Create FastAPI application, environment validation, health endpoint, and structured logging.
- [x] Add MongoDB connection/configuration, collection validation schemas, and indexes for `bounties`, `reviews`, `agent_results`, `disputes`, and `webhook_events`.
- [x] Define Pydantic schemas for review input, agent result, supervisor result, evidence bundle, and API responses.
- [x] Implement idempotency for GitHub deliveries and review keys `(repository, pr_number, commit_sha)`.
- [x] Create a background job/worker boundary so webhook responses return quickly.
- [x] Add configuration for GitHub App, AI provider, IPFS, MongoDB, RPC, contract addresses, and relayer signer.
- [ ] Keep all secrets in environment/secret storage; never return them in API or logs.

## 4. GitHub App and webhook flow

- [x] Create and configure the GitHub App. Read-only authentication was verified against the demo repository.
- [x] Install the GitHub App on the demo repository.
- [x] Implement `POST /webhooks/github` and validate `X-Hub-Signature-256`.
- [x] Handle `pull_request` opened, synchronize, and reopened events.
- [x] Find the matching bounty by repository and issue/PR criteria.
- [x] Fetch the PR metadata, changed files, diff, and head commit SHA.
- [x] Create/update a pending GitHub Check immediately.
- [x] Post a completed check and PR summary after review.
- [ ] Add inline annotations only when a finding can be mapped reliably to a changed line.
- [x] Test duplicate delivery, invalid signature, large diff redaction/truncation, closed PR, and a PR with no matching bounty.

## 5. AI review workflow

- [x] Create the LangGraph state model and validation node.
- [x] Implement the quality agent with typed JSON output.
- [x] Implement the security agent with typed JSON output.
- [x] Implement the spam/low-effort agent with typed JSON output.
- [x] Run the three agents concurrently with timeout, retry, and error capture.
- [x] Implement deterministic supervisor scoring in basis points (0–10,000).
- [x] Flag manual review when an agent score is below 4,000 bps or the score spread exceeds 3,500 bps.
- [x] Keep raw agent results, model identifier, prompt version, and timestamps.
- [x] Add deterministic fixture mode for demonstrations and tests.
- [x] Redact secrets and cap/truncate large diffs before sending them to model providers; record any truncation.

## 6. Evidence, IPFS, and attestation

- [x] Define canonical evidence JSON using the blockchain README schema (`schemaVersion`, bounty ID, repo, PR, commit SHA, scores, reasoning).
- [x] Canonicalize bytes deterministically: UTF-8, sorted keys, stable array ordering, no pretty-print whitespace.
- [x] Calculate `keccak256` over the exact byte sequence uploaded to IPFS.
- [x] Upload/pin those exact bytes and store the returned CID.
- [x] Verify retrieved IPFS content hashes to the same `evidenceHash` before calling the relayer.
- [x] Convert the final score to the contract’s `uint16` basis-point format.
- [x] Send the `submitVerdict` transaction from the relayer service and store its transaction hash.
- [x] Include CID, verdict hash, commit SHA, score, transaction link, and eligibility in the GitHub summary.
- [x] Test a deliberate evidence-byte mutation and confirm verification fails before attestation.

## 7. Dashboard

- [x] Create wallet connection targeting Polygon Amoy.
- [x] Build bounty creation: GitHub Issue URL, reward amount, expiry, recipient policy, ERC-20 approval, and contract transaction status.
- [x] Build active-bounties list with contract and database lifecycle state.
- [x] Build verdict detail: score, agent breakdown, findings, CID, evidence-hash verification, and transaction links.
- [ ] Display challenge countdown and permitted actions.
- [x] Build dispute form that uploads/pins dispute evidence and calls `openDispute`.
- [x] Build resolver-only dispute controls for payout/refund.
- [ ] Show clear pending, confirmed, failed, disputed, and settled states.

## 8. End-to-end verification and submission

- [x] Unit-test schemas, canonicalization, score calculation, and webhook verification.
- [x] Run existing blockchain tests: `npm.cmd test` in `Blockchain/`.
- [ ] Run a testnet happy path: fund → PR webhook → three agent results → IPFS → verdict → challenge window → payout.
- [ ] Run a testnet dispute path: verdict → dispute → resolver refund or payout.
- [ ] Confirm no payout can occur before the challenge deadline or after a dispute is opened.
- [ ] Confirm the PR result is understandable without opening the dashboard.
- [ ] Record a 2–3 minute demo video showing the full happy path and brief dispute path.
- [ ] Prepare Devpost description, architecture diagram, screenshots, repository link, deployed-contract addresses, and demo video.
- [ ] Document setup, environment variables, test commands, and known MVP limitations in the root README.

## Recommended build order

1. Deploy the already-tested contracts to Amoy and save the addresses.
2. Implement the backend schemas, database, contract client, and deterministic fixture workflow.
3. Connect the GitHub App/webhook to the fixture workflow and post checks.
4. Add real agents, canonical evidence, IPFS pinning, and relayer submission.
5. Build the dashboard around live contract and backend states.
6. Run both testnet flows, capture the demo, and finalize the Devpost submission.
