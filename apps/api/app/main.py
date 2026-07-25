import hashlib
import hmac
import json
import logging
import asyncio
import re
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles

from .attestation import AttestationError, attest_review, release_bounty
from .bounties import BountyRegistrationError, registration_message, verify_on_chain_bounty
from .chain import ChainClient, ChainError, build_chain_client
from .config import Settings, get_settings
from .disputes import (
    DisputeError,
    confirm_cancel_open_bounty,
    confirm_dispute_resolution,
    confirm_open_dispute,
    confirm_refund_expired_bounty,
    prepare_cancel_open_bounty,
    prepare_dispute_resolution,
    prepare_open_dispute,
    prepare_refund_expired_bounty,
    refund_expired_bounty_with_service,
    resolve_dispute_with_service,
)
from .event_indexer import monitor_chain_events
from .github import GitHubAppClient
from .ipfs import FixtureIpfsClient, IpfsClient, build_ipfs_client
from .schemas import (
    BountyCreateRequest,
    BountyRegistrationMessageResponse,
    BountyRegistrationRequest,
    BountyResponse,
    DisputeEvidenceRequest,
    DisputeResolutionConfirmationRequest,
    DisputeResolutionRequest,
    GitHubWebhookResponse,
    ReviewInput,
    ReviewResponse,
    TransactionResponse,
    TransactionHashRequest,
    WalletTransactionResponse,
)
from .store import DuplicateBounty, MemoryStore, MongoStore, Store
from .worker import process_fixture_review, process_github_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    application.state.store = MemoryStore() if settings.database_mode == "memory" else MongoStore(settings.mongodb_uri, settings.mongodb_database)
    application.state.ipfs = build_ipfs_client(settings)
    application.state.chain = build_chain_client(settings)
    await application.state.store.ensure_indexes()
    stop_events = asyncio.Event()
    monitor_task = None
    if not settings.fixture_mode:
        monitor_task = asyncio.create_task(monitor_chain_events(application.state.store, application.state.chain, settings, stop_events))
    try:
        yield
    finally:
        stop_events.set()
        if monitor_task is not None:
            await monitor_task


app = FastAPI(title="Fair Bounty Judge API", version="0.1.0", lifespan=lifespan)
app.state.store = MemoryStore()  # Supports local tooling that does not trigger ASGI lifespan.
app.state.ipfs = FixtureIpfsClient()
app.state.chain = build_chain_client(get_settings())

_CLOSING_ISSUE_PATTERN = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s*#(?P<number>\d+)\b",
    re.IGNORECASE,
)


def linked_issue_url(repository: str, pull_request_body: object) -> str | None:
    """Return the issue explicitly closed by the PR in this repository."""
    if not isinstance(pull_request_body, str):
        return None
    match = _CLOSING_ISSUE_PATTERN.search(pull_request_body)
    if match is None:
        return None
    return f"https://github.com/{repository}/issues/{match.group('number')}"


def get_store(request: Request) -> Store:
    return request.app.state.store


def get_ipfs(request: Request) -> IpfsClient:
    return request.app.state.ipfs


def get_chain(request: Request) -> ChainClient:
    return request.app.state.chain


@app.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    return {"status": "ok", "environment": settings.app_env, "fixture_mode": settings.fixture_mode,
            "ai_provider": settings.ai_provider, "github_app_enabled": settings.github_app_enabled}


@app.get("/api/client-config")
async def client_config(settings: Settings = Depends(get_settings)) -> dict[str, int | str | bool | None]:
    explorer_base_url = "https://amoy.polygonscan.com" if settings.chain_id == 80002 else None
    chain_name = "Polygon Amoy" if settings.chain_id == 80002 else "Hardhat Local" if settings.chain_id == 31337 else f"Chain {settings.chain_id}"
    return {
        "chain_id": settings.chain_id,
        "chain_hex": hex(settings.chain_id),
        "chain_name": chain_name,
        "explorer_base_url": explorer_base_url,
        "fixture_mode": settings.fixture_mode,
        "reward_token_address": settings.reward_token_address,
    }


@app.post("/api/reviews/fixture", response_model=ReviewResponse)
async def review_fixture(review: ReviewInput, store: Store = Depends(get_store), ipfs: IpfsClient = Depends(get_ipfs), settings: Settings = Depends(get_settings)) -> ReviewResponse:
    if not settings.fixture_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fixture mode is disabled")
    record, _ = await store.create_review({
        "bounty_id": review.bounty_id,
        "repository": review.repository,
        "pr_number": review.pull_request_number,
        "commit_sha": review.commit_sha,
        "dedupe_key": f"fixture:{uuid4()}",
        "status": "pending",
    })
    return await process_fixture_review(store, ipfs, record["id"], review, settings)


@app.post("/api/bounties/registration-message", response_model=BountyRegistrationMessageResponse)
async def bounty_registration_message(bounty: BountyRegistrationRequest, settings: Settings = Depends(get_settings)) -> dict:
    if settings.fixture_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration signatures are only used for on-chain bounties")
    try:
        return {"message": registration_message(bounty, settings)}
    except BountyRegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.post("/api/bounties/prepare", response_model=WalletTransactionResponse)
async def prepare_bounty_creation(
    bounty: BountyCreateRequest, chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        transaction = await chain.prepare_bounty_creation(
            bounty.contract_bounty_id, bounty.reward_token, int(bounty.reward_amount), bounty.expires_at
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"operation": "create_bounty", "transaction": transaction}


@app.post("/api/bounties", response_model=BountyResponse, status_code=status.HTTP_201_CREATED)
async def create_bounty(
    bounty: BountyRegistrationRequest,
    store: Store = Depends(get_store),
    chain: ChainClient = Depends(get_chain),
    settings: Settings = Depends(get_settings),
) -> dict:
    values = bounty.model_dump(exclude={"registration_signature"})
    if not settings.fixture_mode:
        try:
            values.update(await verify_on_chain_bounty(bounty, chain, settings))
        except BountyRegistrationError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    try:
        return await store.create_bounty(values | {"status": "open"})
    except DuplicateBounty as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bounty is already registered") from exc


@app.get("/api/bounties", response_model=list[BountyResponse])
async def list_bounties(store: Store = Depends(get_store)) -> list[dict]:
    return await store.list_bounties()


@app.get("/api/bounties/{contract_bounty_id}", response_model=BountyResponse)
async def get_bounty(contract_bounty_id: str, store: Store = Depends(get_store)) -> dict:
    bounty = await store.get_bounty(contract_bounty_id)
    if bounty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty was not found")
    return bounty


@app.get("/api/bounties/{contract_bounty_id}/chain-state")
async def get_bounty_chain_state(contract_bounty_id: str, chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        return {
            "bounty": await chain.get_bounty(contract_bounty_id),
            "verdict": await chain.get_verdict(contract_bounty_id),
            "dispute": await chain.get_dispute(contract_bounty_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/disputes")
async def list_disputes(store: Store = Depends(get_store)) -> list[dict]:
    return await store.list_disputes()


@app.get("/api/bounties/{contract_bounty_id}/dispute")
async def get_dispute(contract_bounty_id: str, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        return {"local": await store.get_dispute(contract_bounty_id), "chain": await chain.get_dispute(contract_bounty_id)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/transactions/{transaction_hash}", response_model=TransactionResponse)
async def get_transaction_status(transaction_hash: str, chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        return await chain.get_transaction_status(transaction_hash)
    except ChainError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/disputes/prepare", response_model=WalletTransactionResponse)
async def prepare_bounty_dispute(
    contract_bounty_id: str,
    payload: DisputeEvidenceRequest,
    store: Store = Depends(get_store),
    chain: ChainClient = Depends(get_chain),
    ipfs: IpfsClient = Depends(get_ipfs),
) -> dict:
    try:
        result = await prepare_open_dispute(store, chain, ipfs, contract_bounty_id, payload.evidence)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "operation": "open_dispute",
        "transaction": result["transaction"],
        "evidence_cid": result["evidence_cid"],
        "evidence_hash": result["evidence_hash"],
        "dispute_status": "transaction_prepared",
    }


@app.post("/api/bounties/{contract_bounty_id}/disputes/confirm", response_model=TransactionResponse)
async def confirm_bounty_dispute(
    contract_bounty_id: str, payload: TransactionHashRequest, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await confirm_open_dispute(store, chain, contract_bounty_id, payload.transaction_hash)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/disputes/resolve/prepare", response_model=WalletTransactionResponse)
async def prepare_bounty_dispute_resolution(
    contract_bounty_id: str, payload: DisputeResolutionRequest, chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        transaction = await prepare_dispute_resolution(chain, contract_bounty_id, payload.resolution)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"operation": "resolve_dispute", "transaction": transaction}


@app.post("/api/bounties/{contract_bounty_id}/disputes/resolve/confirm", response_model=TransactionResponse)
async def confirm_bounty_dispute_resolution(
    contract_bounty_id: str, payload: DisputeResolutionConfirmationRequest,
    store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await confirm_dispute_resolution(store, chain, contract_bounty_id, payload.resolution, payload.transaction_hash)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/disputes/resolve", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def resolve_bounty_dispute_with_service(
    contract_bounty_id: str, payload: DisputeResolutionRequest, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await resolve_dispute_with_service(store, chain, contract_bounty_id, payload.resolution)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/cancel/prepare", response_model=WalletTransactionResponse)
async def prepare_bounty_cancellation(contract_bounty_id: str, chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        transaction = await prepare_cancel_open_bounty(chain, contract_bounty_id)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"operation": "cancel_open_bounty", "transaction": transaction}


@app.post("/api/bounties/{contract_bounty_id}/cancel/confirm", response_model=TransactionResponse)
async def confirm_bounty_cancellation(
    contract_bounty_id: str, payload: TransactionHashRequest, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await confirm_cancel_open_bounty(store, chain, contract_bounty_id, payload.transaction_hash)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/refund/prepare", response_model=WalletTransactionResponse)
async def prepare_expired_bounty_refund(contract_bounty_id: str, chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        transaction = await prepare_refund_expired_bounty(chain, contract_bounty_id)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"operation": "refund_expired_bounty", "transaction": transaction}


@app.post("/api/bounties/{contract_bounty_id}/refund/confirm", response_model=TransactionResponse)
async def confirm_expired_bounty_refund(
    contract_bounty_id: str, payload: TransactionHashRequest, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await confirm_refund_expired_bounty(store, chain, contract_bounty_id, payload.transaction_hash)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/refund", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def refund_expired_bounty_service_endpoint(
    contract_bounty_id: str, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)
) -> dict:
    try:
        return await refund_expired_bounty_with_service(store, chain, contract_bounty_id)
    except DisputeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: str, store: Store = Depends(get_store)) -> dict:
    review = await store.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review was not found")
    return review


@app.get("/api/reviews/{review_id}/evidence")
async def get_review_evidence(review_id: str, store: Store = Depends(get_store)) -> Response:
    evidence = await store.get_evidence(review_id)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review evidence was not found")
    return Response(content=evidence["evidence_bytes"], media_type="application/json", headers={
        "X-Evidence-Hash": evidence["evidence_hash"],
        "X-Evidence-Cid": evidence["evidence_cid"],
    })


@app.post("/api/reviews/{review_id}/attest", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def attest_review_endpoint(review_id: str, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain), ipfs: IpfsClient = Depends(get_ipfs)) -> dict:
    try:
        return await attest_review(store, chain, ipfs, review_id)
    except AttestationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@app.post("/api/bounties/{contract_bounty_id}/release", response_model=TransactionResponse, status_code=status.HTTP_202_ACCEPTED)
async def release_bounty_endpoint(contract_bounty_id: str, store: Store = Depends(get_store), chain: ChainClient = Depends(get_chain)) -> dict:
    try:
        return await release_bounty(store, chain, contract_bounty_id)
    except AttestationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _verified_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, "sha256=" + digest)


@app.post("/", response_model=GitHubWebhookResponse, status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
@app.post("/webhooks/github", response_model=GitHubWebhookResponse, status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(request: Request, background_tasks: BackgroundTasks, x_hub_signature_256: str | None = Header(default=None), x_github_delivery: str | None = Header(default=None), settings: Settings = Depends(get_settings), store: Store = Depends(get_store)) -> GitHubWebhookResponse:
    payload = await request.body()
    if not _verified_signature(payload, x_hub_signature_256, settings.github_webhook_secret.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature")
    try:
        event = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc
    # GitHub sends ``edited`` when a contributor adds or corrects the closing
    # issue reference in the PR description after opening the PR.  That
    # description is the bounty matching source, so it must trigger matching
    # too.  ``dedupe_key`` still prevents a second review for the same commit.
    if request.headers.get("x-github-event") != "pull_request" or event.get("action") not in {"opened", "synchronize", "reopened", "edited"}:
        return GitHubWebhookResponse(request_id=str(uuid4()), status="ignored", delivery_id=x_github_delivery or "missing")
    delivery_id = x_github_delivery or hashlib.sha256(payload).hexdigest()
    if not await store.record_delivery(delivery_id, "pull_request", hashlib.sha256(payload).hexdigest()):
        return GitHubWebhookResponse(request_id=str(uuid4()), status="duplicate", delivery_id=delivery_id)
    repository = event.get("repository", {}).get("full_name")
    pull_request = event.get("pull_request", {})
    issue_url = linked_issue_url(repository, pull_request.get("body"))
    logger.info("github webhook received", extra={"delivery_id": delivery_id, "repository": repository, "issue_url": issue_url, "pr_number": pull_request.get("number")})
    if settings.github_allowed_repositories and repository not in settings.github_allowed_repositories:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Repository is not allowlisted")
    bounty = await store.find_bounty(repository, issue_url) if issue_url else None
    if bounty is None:
        logger.info("no matching bounty for PR", extra={"repository": repository, "issue_url": issue_url, "delivery_id": delivery_id})
        return GitHubWebhookResponse(request_id=str(uuid4()), status="no_matching_bounty", delivery_id=delivery_id)
    installation_id = event.get("installation", {}).get("id")
    commit_sha = pull_request.get("head", {}).get("sha")
    number = event.get("number")
    if not isinstance(commit_sha, str) or not isinstance(number, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed pull request payload")
    review_record, created = await store.create_review({"bounty_id": bounty["contract_bounty_id"], "repository": repository,
        "pr_number": number, "commit_sha": commit_sha, "dedupe_key": f"{repository}:{number}:{commit_sha}", "github_installation_id": installation_id, "status": "pending"})
    has_github_installation = installation_id is not None or settings.github_installation_id is not None
    if created and settings.github_app_enabled and has_github_installation:
        check_run_id = await GitHubAppClient(settings, installation_id).create_pending_check(repository, commit_sha)
        await store.update_review(review_record["id"], {"github_check_run_id": check_run_id})
        review_record["github_check_run_id"] = check_run_id
        background_tasks.add_task(
            process_github_review,
            store,
            request.app.state.ipfs,
            request.app.state.chain,
            review_record["id"],
            review_record,
            bounty,
            settings,
        )
    elif created and settings.fixture_mode:
        review_input = ReviewInput(bounty_id=bounty["contract_bounty_id"], repository=repository, pull_request_number=number,
            commit_sha=commit_sha, title=pull_request.get("title", "Untitled"), body=pull_request.get("body"), diff="",
            changed_files=[], author=pull_request.get("user", {}).get("login", "unknown"), criteria=bounty["criteria"])
        background_tasks.add_task(process_fixture_review, store, request.app.state.ipfs, review_record["id"], review_input, settings)
    return GitHubWebhookResponse(request_id=str(uuid4()), status="accepted" if created else "duplicate_review", delivery_id=delivery_id)


web_directory = Path(__file__).resolve().parents[2] / "web"
app.mount("/app", StaticFiles(directory=web_directory, html=True), name="dashboard")
