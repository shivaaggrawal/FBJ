# Fair Bounty Judge — Build Checklist

## Current baseline

The blockchain implementation in `Blockchain/` is substantially complete and verified locally: `npm.cmd test` passes **10/10 tests**. It uses ERC-20 rewards on Polygon Amoy, not native-token deposits. The application must integrate with its existing interfaces rather than rebuild contracts.

## 0. Decisions to lock before wiring components

- [ ] Select the AI model/provider and record model names, prompt versions, and data-retention settings.
- [ ] Select the IPFS pinning provider and create an API credential.
- [ ] Select a MongoDB deployment (local Docker or MongoDB Atlas) and create a development database.
- [ ] Choose the GitHub organization/repository used for the live demo.
- [ ] Confirm the reward ERC-20 token deployed on Polygon Amoy (test token only).
- [ ] Confirm the relayer wallet and dispute-resolver wallet.
- [ ] Decide the demo score policy: current chain threshold is 7,000 bps (70%).
- [ ] Decide the demo challenge period: current deployment script default is three days; use a short test/demo period only in a dedicated demo deployment.

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

- [ ] Create `Blockchain/.env` locally from `.env.example`; never commit it.
- [ ] Fund deployment and relayer wallets with Amoy POL for gas.
- [ ] Deploy or choose a test ERC-20 reward token on Amoy.
- [ ] Set `AMOY_RPC_URL`, `DEPLOYER_PRIVATE_KEY`, `DEFAULT_REWARD_TOKEN`, `RELAYER_ADDRESS`, and `DISPUTE_RESOLVER_ADDRESS`.
- [ ] Deploy with `npm.cmd run deploy:amoy` and save the returned chain ID and three contract addresses in non-secret application configuration.
- [ ] Verify each deployed contract on the selected explorer if time permits.
- [ ] Confirm roles after deployment: registry has escrow registry role; dispute manager has escrow dispute role; relayer has registry relayer role; resolver has dispute role.
- [x] Add an application contract configuration object: `chainId`, `bountyEscrow`, `verdictRegistry`, `disputeManager`, `rewardToken`.
- [ ] Generate/use ABIs and typed contract clients in the backend and dashboard.
- [ ] Implement backend calls to existing functions:
  - [ ] `createBounty(bytes32,address,uint128,uint64)` after user approves the ERC-20 allowance.
  - [x] `submitVerdict(bytes32,bytes32,string,address,uint16)` from the relayer service.
  - [x] `releaseBounty(bytes32)` after the challenge deadline.
  - [ ] `openDispute(bytes32,string)` from the connected maintainer/recipient wallet.
  - [ ] `resolveDispute(bytes32,Resolution)` from the designated resolver.
- [ ] Subscribe to `BountyCreated`, `VerdictSubmitted`, `DisputeOpened`, `BountyPaid`, and `BountyRefunded`; persist transaction hashes and statuses.
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

- [ ] Create a GitHub App with only required permissions: Checks read/write, Pull requests read/write, Contents read, Issues read.
- [ ] Install it only on the demo repository.
- [x] Implement `POST /webhooks/github` and validate `X-Hub-Signature-256`.
- [x] Handle `pull_request` opened, synchronize, and reopened events.
- [ ] Find the matching bounty by repository and issue/PR criteria.
- [ ] Fetch the PR metadata, changed files, diff, and head commit SHA.
- [ ] Create/update a pending GitHub Check immediately.
- [ ] Post a completed check and PR summary after review.
- [ ] Add inline annotations only when a finding can be mapped reliably to a changed line.
- [ ] Test duplicate delivery, invalid signature, large diff, closed PR, and a PR with no matching bounty.

## 5. AI review workflow

- [ ] Create the LangGraph state model and validation node.
- [ ] Implement the quality agent with typed JSON output.
- [ ] Implement the security agent with typed JSON output.
- [ ] Implement the spam/low-effort agent with typed JSON output.
- [ ] Run the three agents concurrently with timeout, retry, and error capture.
- [x] Implement deterministic supervisor scoring in basis points (0–10,000).
- [x] Flag manual review when an agent score is below 4,000 bps or the score spread exceeds 3,500 bps.
- [x] Keep raw agent results, model identifier, prompt version, and timestamps.
- [x] Add deterministic fixture mode for demonstrations and tests.
- [ ] Redact secrets and cap/truncate large diffs before sending them to model providers; record any truncation.

## 6. Evidence, IPFS, and attestation

- [x] Define canonical evidence JSON using the blockchain README schema (`schemaVersion`, bounty ID, repo, PR, commit SHA, scores, reasoning).
- [x] Canonicalize bytes deterministically: UTF-8, sorted keys, stable array ordering, no pretty-print whitespace.
- [x] Calculate `keccak256` over the exact byte sequence uploaded to IPFS.
- [x] Upload/pin those exact bytes and store the returned CID.
- [ ] Verify retrieved IPFS content hashes to the same `evidenceHash` before calling the relayer.
- [x] Convert the final score to the contract’s `uint16` basis-point format.
- [x] Send the `submitVerdict` transaction from the relayer service and store its transaction hash.
- [ ] Include CID, verdict hash, commit SHA, score, transaction link, and eligibility in the GitHub summary.
- [ ] Test a deliberate evidence-byte mutation and confirm verification fails before attestation.

## 7. Dashboard

- [ ] Create wallet connection targeting Polygon Amoy.
- [ ] Build bounty creation: GitHub Issue URL, reward amount, expiry, recipient policy, ERC-20 approval, and contract transaction status.
- [ ] Build active-bounties list with contract and database lifecycle state.
- [ ] Build verdict detail: score, agent breakdown, findings, CID, evidence-hash verification, and transaction links.
- [ ] Display challenge countdown and permitted actions.
- [ ] Build dispute form that uploads/pins dispute evidence and calls `openDispute`.
- [ ] Build resolver-only dispute controls for payout/refund.
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
