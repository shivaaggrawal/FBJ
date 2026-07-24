# Fair Bounty Judge API

The API provides a FastAPI health endpoint, signed GitHub webhook ingress, deterministic review evidence, content-addressed evidence storage, and relayer-backed verdict submission.

## Run locally

```powershell
# From the repository root. Requires the Windows Python 3.10 launcher.
.\apps\api\scripts\setup-dev.ps1
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir apps\api

# Run the pinned test environment.
.\apps\api\scripts\setup-dev.ps1 -RunTests
```

`setup-dev.ps1` always uses an isolated repository-root `.venv` with Python 3.10 and installs the exact versions in `requirements.txt`. The repository-root `.env` is the only environment file used by the API and Hardhat; do not commit it.

Fixture review is available at `POST /api/reviews/fixture` only when `FIXTURE_MODE=true`. It uses deterministic review output, an in-process IPFS-compatible CID, and a fixture chain client, so the entire evidence-to-verdict path can be exercised without credentials.

Run the complete local bounty, review, evidence, attestation, and payout flow without Amoy POL:

```powershell
python scripts/fixture_e2e.py
```

The browser dashboard is served by the API at `http://127.0.0.1:8000/app/`. It connects an Amoy wallet, prepares ERC-20 approval and bounty transactions, registers confirmed bounties, displays evidence/review state, and prepares wallet-signed dispute, cancellation, refund, and resolver actions.

## MongoDB development mode

For durable local state, start MongoDB with `docker compose -f ../../infra/docker-compose.yml up -d`, then set `DATABASE_MODE=mongodb` in `.env`. Startup creates collection validation rules and indexes for bounties, reviews, evidence, agent results, disputes, and webhook deliveries. The default `memory` mode needs no external services and is intended for tests and fixture demos.

## Evidence And Attestation

The API accepts registered bounty metadata, receives signed GitHub pull-request webhooks, stores deterministic review evidence, and can publish eligible evidence to `VerdictRegistry` through a relayer key.

Core endpoints:

- `POST /api/bounties` registers a bounty only after fixture creation or verified on-chain creation.
- `GET /api/bounties` and `GET /api/bounties/{contract_bounty_id}` return local lifecycle state.
- `POST /api/reviews/fixture` runs the deterministic local review and persists its exact evidence bytes.
- `GET /api/reviews/{review_id}` and `GET /api/reviews/{review_id}/evidence` expose review state and the canonical JSON that was hashed.
- `POST /api/reviews/{review_id}/attest` submits an eligible verdict through the configured relayer.
- `POST /api/bounties/{contract_bounty_id}/release` calls `BountyEscrow.releaseBounty` after the contract's challenge window has passed.
- `POST /api/bounties/prepare` returns the ERC-20 approval and `createBounty` wallet transactions.
- `POST /api/bounties/{contract_bounty_id}/disputes/prepare` pins and verifies dispute evidence, then returns an `openDispute` wallet transaction.
- `POST /api/bounties/{contract_bounty_id}/disputes/confirm`, `/disputes/resolve/confirm`, `/cancel/confirm`, and `/refund/confirm` verify wallet-signed receipts, persist the transaction hash/status, and update local lifecycle state.
- `GET /api/bounties/{contract_bounty_id}/dispute` returns both the persisted dispute record and `DisputeManager.getDispute` state; `GET /api/transactions/{transaction_hash}` reports pending, confirmed, or failed receipt status.
- `POST /api/bounties/{contract_bounty_id}/disputes/resolve` broadcasts a resolver-authorized decision only when `DISPUTE_RESOLVER_PRIVATE_KEY` is configured. `POST /api/bounties/{contract_bounty_id}/refund` broadcasts an expired-bounty refund from the service wallet.

Maintainer/recipient actions (`openDispute` and `cancelOpenBounty`) remain wallet-signed: the API never holds those private keys. The dashboard waits for a wallet receipt and then calls the matching `/confirm` endpoint. Chain event indexing also reconciles `DisputeOpened` and `DisputeResolved` events into the local record for transactions submitted outside the dashboard.

Set `FIXTURE_MODE=false`, `DATABASE_MODE=mongodb`, `IPFS_PROVIDER=pinata`, and the deployment values in `.env` to enable the real Amoy + Pinata flow. The relayer private key must only hold `RELAYER_ROLE`; review code must never receive it.

The attestation endpoint never accepts a payout address from its caller. It uses only the `recipient_wallet` saved with the verified bounty registration, re-fetches the evidence CID from IPFS, and verifies its Keccak hash before submitting the relayer transaction.

## Creating A Real Bounty

The API deliberately does not hold a maintainer private key. A maintainer wallet must approve the ERC-20 and call `BountyEscrow.createBounty`; the API then verifies the confirmed transaction, the `BountyCreated` event, the escrow fields, and a wallet signature before it saves the GitHub mapping.

1. Set the deployed Amoy addresses and `FIXTURE_MODE=false` in the repository-root `.env`, then start MongoDB and the API.
2. From `Blockchain/`, set the same escrow address and the maintainer wallet in its local `.env`, then run `npm.cmd run bounty:create -- <escrow> <token-or-zero-address> <bounty-id> <token-smallest-unit-amount> <expiry-unix>`.
3. Submit the creation metadata, transaction hash, and maintainer signature to `POST /api/bounties`. Request `POST /api/bounties/registration-message` with the same payload first to obtain the exact message to sign with `personal_sign`.

`expires_at` is the exact Unix timestamp submitted to the contract. `challenge_seconds` is retained as application metadata; the deployed `VerdictRegistry` challenge period controls the actual on-chain release delay.

## Chain Adapter Capabilities

The backend adapter prepares unsigned wallet transactions for bounty creation, cancellation, opening disputes, and resolver approval. It broadcasts only operations that are safe for its configured service wallets: verdict submission, payout release, expired-bounty refunds, and optionally dispute resolution when `DISPUTE_RESOLVER_PRIVATE_KEY` is configured. It also reads bounties, verdicts, disputes, and normalized contract events for database reconciliation.

In non-fixture mode the API polls confirmed contract events and stores a replay-safe cursor in MongoDB. Set `CHAIN_EVENT_START_BLOCK` to the deployment block to index earlier activity; leaving it empty starts at the current confirmed block.
