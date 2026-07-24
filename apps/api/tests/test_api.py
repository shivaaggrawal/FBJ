import hashlib
import hmac

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)
settings = Settings()
repository = settings.github_allowed_repositories[0] if settings.github_allowed_repositories else "owner/demo-repository"
webhook_secret = settings.github_webhook_secret.get_secret_value()


def create_bounty():
    return client.post("/api/bounties", json={"contract_bounty_id": "0x" + "ab" * 32, "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    health = response.json()
    assert health == {
        "status": "ok",
        "environment": settings.app_env,
        "fixture_mode": settings.fixture_mode,
        "ai_provider": settings.ai_provider,
        "github_app_enabled": settings.github_app_enabled,
    }
    assert webhook_secret not in response.text


def test_dashboard_is_served_by_the_api():
    response = client.get("/app/")
    assert response.status_code == 200
    assert "Fair Bounty Judge" in response.text


def test_invalid_webhook_signature_is_rejected():
    response = client.post("/webhooks/github", content=b"{}", headers={"X-Hub-Signature-256": "sha256=invalid"})
    assert response.status_code == 401


def test_root_path_accepts_signed_github_webhooks_for_tunnel_compatibility():
    payload = b'{"action":"closed"}'
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/", content=payload, headers={
        "X-Hub-Signature-256": "sha256=" + signature,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "root-path-delivery",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"


def test_closed_webhook_is_ignored():
    payload = (f'{{"action":"closed","number":1,"repository":{{"full_name":"{repository}"}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={
        "X-Hub-Signature-256": "sha256=" + signature,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "closed-delivery",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"


def test_webhook_without_matching_bounty_is_reported():
    payload = (f'{{"action":"opened","number":1,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={
        "X-Hub-Signature-256": "sha256=" + signature,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "no-bounty-delivery",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "no_matching_bounty"


def test_valid_supported_webhook_is_accepted():
    assert create_bounty().status_code == 201
    payload = (f'{{"action":"opened","number":1,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-1"})
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_duplicate_delivery_is_idempotent():
    payload = (f'{{"action":"opened","number":2,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    headers = {"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "duplicate-delivery"}
    first, second = client.post("/webhooks/github", content=payload, headers=headers), client.post("/webhooks/github", content=payload, headers=headers)
    assert first.json()["status"] == "accepted"
    assert second.json()["status"] == "duplicate"


def test_fixture_review_persists_evidence_and_supports_attestation():
    bounty_id = "0x" + "cd" * 32
    recipient_wallet = "0x" + "9a" * 20
    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": "owner/attestation-demo",
        "issue_url": "https://github.com/owner/attestation-demo/issues/1", "reward_token": "0x" + "56" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "78" * 20, "recipient_wallet": recipient_wallet, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert bounty.status_code == 201

    review = client.post("/api/reviews/fixture", json={"bounty_id": bounty_id, "repository": "owner/attestation-demo",
        "pull_request_number": 9, "commit_sha": "b" * 40, "title": "Eligible change", "diff": "diff --git a/a.py b/a.py",
        "changed_files": [], "author": "developer"})
    assert review.status_code == 200
    payload = review.json()
    assert payload["evidence_cid"].startswith("Qm")

    evidence = client.get(f"/api/reviews/{payload['review_id']}/evidence")
    assert evidence.status_code == 200
    assert evidence.headers["x-evidence-hash"] == payload["evidence_hash"]
    assert evidence.headers["x-evidence-cid"] == payload["evidence_cid"]

    attestation = client.post(f"/api/reviews/{payload['review_id']}/attest", json={"recipient_wallet": "0x" + "ff" * 20})
    assert attestation.status_code == 202
    assert attestation.json()["status"] == "confirmed"
    assert client.get(f"/api/reviews/{payload['review_id']}").json()["recipient_wallet"] == recipient_wallet

    release = client.post(f"/api/bounties/{bounty_id}/release")
    assert release.status_code == 202
    assert client.get(f"/api/bounties/{bounty_id}").json()["status"] == "paid_out"


def test_duplicate_bounty_registration_is_rejected():
    assert create_bounty().status_code == 409


def test_wallet_preparation_endpoints_return_unsigned_actions():
    bounty_id = "0x" + "ef" * 32
    create = client.post("/api/bounties/prepare", json={"contract_bounty_id": bounty_id, "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/3", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert create.status_code == 200
    assert create.json()["transaction"]["approval"]["operation"] == "approve"

    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": "owner/dispute-demo",
        "issue_url": "https://github.com/owner/dispute-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert bounty.status_code == 201

    dispute = client.post(f"/api/bounties/{bounty_id}/disputes/prepare", json={"evidence": {"reason": "needs adjudication"}})
    assert dispute.status_code == 200
    assert dispute.json()["transaction"]["operation"] == "open_dispute"
    assert dispute.json()["evidence_cid"].startswith("Qm")

    resolution = client.post(f"/api/bounties/{bounty_id}/disputes/resolve/prepare", json={"resolution": 2})
    assert resolution.status_code == 200
    assert resolution.json()["transaction"]["operation"] == "resolve_dispute"

    assert client.post(f"/api/bounties/{bounty_id}/cancel/prepare").json()["transaction"]["operation"] == "cancel_open_bounty"
    assert client.post(f"/api/bounties/{bounty_id}/refund/prepare").json()["transaction"]["operation"] == "refund_expired_bounty"


def test_wallet_action_confirmations_persist_dispute_and_bounty_states():
    bounty_id = "0x" + "fa" * 32
    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": "owner/confirmation-demo",
        "issue_url": "https://github.com/owner/confirmation-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert bounty.status_code == 201

    prepared = client.post(f"/api/bounties/{bounty_id}/disputes/prepare", json={"evidence": {"reason": "verify confirmation"}})
    assert prepared.status_code == 200
    dispute_hash = "0x" + "11" * 32
    opened = client.post(f"/api/bounties/{bounty_id}/disputes/confirm", json={"transaction_hash": dispute_hash})
    assert opened.status_code == 200
    assert opened.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{bounty_id}/dispute").json()["chain"]["open"] is True
    assert client.get(f"/api/bounties/{bounty_id}").json()["status"] == "challenged"

    resolution = client.post(f"/api/bounties/{bounty_id}/disputes/resolve/confirm", json={"resolution": 2, "transaction_hash": "0x" + "22" * 32})
    assert resolution.status_code == 200
    assert resolution.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{bounty_id}").json()["status"] == "refunded"
    assert client.get(f"/api/transactions/{dispute_hash}").json()["status"] == "confirmed"

    cancelled_bounty = "0x" + "fb" * 32
    assert client.post("/api/bounties", json={"contract_bounty_id": cancelled_bounty, "repository": "owner/cancel-demo",
        "issue_url": "https://github.com/owner/cancel-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600}).status_code == 201
    cancelled = client.post(f"/api/bounties/{cancelled_bounty}/cancel/confirm", json={"transaction_hash": "0x" + "33" * 32})
    assert cancelled.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{cancelled_bounty}").json()["status"] == "cancelled"

    refunded_bounty = "0x" + "fc" * 32
    assert client.post("/api/bounties", json={"contract_bounty_id": refunded_bounty, "repository": "owner/refund-demo",
        "issue_url": "https://github.com/owner/refund-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600}).status_code == 201
    refunded = client.post(f"/api/bounties/{refunded_bounty}/refund/confirm", json={"transaction_hash": "0x" + "44" * 32})
    assert refunded.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{refunded_bounty}").json()["status"] == "refunded"
