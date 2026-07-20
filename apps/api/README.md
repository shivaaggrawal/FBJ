# Fair Bounty Judge API

The first application increment provides a FastAPI health endpoint, signed GitHub webhook ingress, typed review schemas, deterministic fixture agents, basis-point supervision, and canonical Keccak evidence hashing.

## Run locally

```powershell
cd apps/api
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
python -m pytest
```

Fixture review is available at `POST /api/reviews/fixture` only when `FIXTURE_MODE=true`. It intentionally has no AI, IPFS, database, GitHub App, or relayer credentials; those integrations are the next checklist increments.

## MongoDB development mode

For durable local state, start MongoDB with `docker compose -f ../../infra/docker-compose.yml up -d`, then set `DATABASE_MODE=mongodb` in `.env`. Startup creates collection validation rules and the checklist indexes for bounties, reviews, agent results, disputes, and webhook deliveries. The default `memory` mode needs no external services and is intended for tests and fixture demos.
