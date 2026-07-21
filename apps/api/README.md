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

- `POST /api/bounties` registers the GitHub-to-on-chain bounty mapping.
- `GET /api/bounties` and `GET /api/bounties/{contract_bounty_id}` return local lifecycle state.
- `POST /api/reviews/fixture` runs the deterministic local review and persists its exact evidence bytes.
- `GET /api/reviews/{review_id}` and `GET /api/reviews/{review_id}/evidence` expose review state and the canonical JSON that was hashed.
- `POST /api/reviews/{review_id}/attest` submits an eligible verdict through the configured relayer.
- `POST /api/bounties/{contract_bounty_id}/release` calls `BountyEscrow.releaseBounty` after the contract's challenge window has passed.

Set `FIXTURE_MODE=false`, `DATABASE_MODE=mongodb`, `IPFS_PROVIDER=pinata`, and the deployment values in `.env` to enable the real Amoy + Pinata flow. The relayer private key must only hold `RELAYER_ROLE`; review code must never receive it.
