import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status

from .config import Settings, get_settings
from .github import GitHubAppClient
from .schemas import BountyCreateRequest, BountyResponse, GitHubWebhookResponse, ReviewInput, ReviewResponse
from .store import MemoryStore, MongoStore, Store
from .worker import process_fixture_review, process_github_review
from .workflow import run_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    application.state.store = MemoryStore() if settings.database_mode == "memory" else MongoStore(settings.mongodb_uri, settings.mongodb_database)
    await application.state.store.ensure_indexes()
    yield


app = FastAPI(title="Fair Bounty Judge API", version="0.1.0", lifespan=lifespan)
app.state.store = MemoryStore()  # Supports local tooling that does not trigger ASGI lifespan.


def get_store(request: Request) -> Store:
    return request.app.state.store


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    return {"status": "ok", "environment": settings.app_env, "fixture_mode": settings.fixture_mode,
            "ai_provider": settings.ai_provider, "github_app_enabled": settings.github_app_enabled}


@app.post("/api/reviews/fixture", response_model=ReviewResponse)
async def review_fixture(review: ReviewInput, settings: Settings = Depends(get_settings)) -> ReviewResponse:
    if not settings.fixture_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixture mode is disabled")
    return await run_review(review, settings)


@app.post("/api/bounties", response_model=BountyResponse, status_code=status.HTTP_201_CREATED)
async def create_bounty(bounty: BountyCreateRequest, store: Store = Depends(get_store)) -> dict:
    return await store.create_bounty(bounty.model_dump() | {"status": "open"})


def _verified_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, "sha256=" + digest)


@app.post("/webhooks/github", response_model=GitHubWebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: str | None = Header(default=None), x_github_delivery: str | None = Header(default=None), settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> GitHubWebhookResponse:
    payload = await request.body()
    if not _verified_signature(payload, x_hub_signature_256, settings.github_webhook_secret.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature")
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc
    if request.headers.get("x-github-event") != "pull_request" or event.get("action") not in {"opened", "synchronize", "reopened"}:
        return GitHubWebhookResponse(request_id=str(uuid4()), status="ignored", delivery_id=x_github_delivery or "missing")
    delivery_id = x_github_delivery or hashlib.sha256(payload).hexdigest()
    if not await store.record_delivery(delivery_id, "pull_request", hashlib.sha256(payload).hexdigest()):
        return GitHubWebhookResponse(request_id=str(uuid4()), status="duplicate", delivery_id=delivery_id)
    repository = event.get("repository", {}).get("full_name")
    if settings.github_allowed_repositories and repository not in settings.github_allowed_repositories:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Repository is not allowlisted")
    bounty = await store.find_bounty(repository)
    if bounty is None:
        return GitHubWebhookResponse(request_id=str(uuid4()), status="no_matching_bounty", delivery_id=delivery_id)
    pull_request = event.get("pull_request", {})
    installation_id = event.get("installation", {}).get("id")
    commit_sha = pull_request.get("head", {}).get("sha")
    number = event.get("number")
    if not isinstance(commit_sha, str) or not isinstance(number, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed pull request payload")
    review_record, created = await store.create_review({"bounty_id": bounty["contract_bounty_id"], "repository": repository,
        "pr_number": number, "commit_sha": commit_sha, "dedupe_key": f"{repository}:{number}:{commit_sha}", "github_installation_id": installation_id, "status": "pending"})
    if created and settings.github_app_enabled:
        check_run_id = await GitHubAppClient(settings, installation_id).create_pending_check(repository, commit_sha)
        await store.update_review(review_record["id"], {"github_check_run_id": check_run_id})
        review_record["github_check_run_id"] = check_run_id
        background_tasks.add_task(process_github_review, store, review_record["id"], review_record, bounty, settings)
    elif created and settings.fixture_mode:
        review_input = ReviewInput(bounty_id=bounty["contract_bounty_id"], repository=repository, pull_request_number=number,
            commit_sha=commit_sha, title=pull_request.get("title", "Untitled"), body=pull_request.get("body"), diff="",
            changed_files=[], author=pull_request.get("user", {}).get("login", "unknown"), criteria=bounty["criteria"])
        background_tasks.add_task(process_fixture_review, store, review_record["id"], review_input, settings)
    return GitHubWebhookResponse(request_id=str(uuid4()), status="accepted" if created else "duplicate_review", delivery_id=delivery_id)
