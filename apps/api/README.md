# Fair Bounty Judge API

The API provides a FastAPI health endpoint, signed GitHub webhook ingress, deterministic review evidence, content-addressed evidence storage, and relayer-backed verdict submission.

## Run locally

```powershell
cd apps/api
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
python -m pytest
```

Fixture review is available at `POST /api/reviews/fixture` only when `FIXTURE_MODE=true`. It uses deterministic review output, an in-process IPFS-compatible CID, and a fixture chain client, so the entire evidence-to-verdict path can be exercised without credentials.

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

Set `FIXTURE_MODE=false`, `DATABASE_MODE=mongodb`, `IPFS_PROVIDER=pinata`, and the deployment values in `.env` to enable the real Amoy + Pinata flow. The relayer private key must only hold `RELAYER_ROLE`; review code must never receive it.

## Creating A Real Bounty

The API deliberately does not hold a maintainer private key. A maintainer wallet must approve the ERC-20 and call `BountyEscrow.createBounty`; the API then verifies the confirmed transaction, the `BountyCreated` event, the escrow fields, and a wallet signature before it saves the GitHub mapping.

1. Set the deployed Amoy addresses and `FIXTURE_MODE=false` in `apps/api/.env`, then start MongoDB and the API.
2. From `Blockchain/`, set the same escrow address and the maintainer wallet in its local `.env`, then run `npm.cmd run bounty:create -- <escrow> <token-or-zero-address> <bounty-id> <token-smallest-unit-amount> <expiry-unix>`.
3. Submit the creation metadata, transaction hash, and maintainer signature to `POST /api/bounties`. Request `POST /api/bounties/registration-message` with the same payload first to obtain the exact message to sign with `personal_sign`.

`expires_at` is the exact Unix timestamp submitted to the contract. `challenge_seconds` is retained as application metadata; the deployed `VerdictRegistry` challenge period controls the actual on-chain release delay.
