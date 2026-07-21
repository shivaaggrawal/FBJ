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
    assert response.json()["fixture_mode"] is True


def test_invalid_webhook_signature_is_rejected():
    response = client.post("/webhooks/github", content=b"{}", headers={"X-Hub-Signature-256": "sha256=invalid"})
    assert response.status_code == 401


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
    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": "owner/attestation-demo",
        "issue_url": "https://github.com/owner/attestation-demo/issues/1", "reward_token": "0x" + "56" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "78" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
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

    attestation = client.post(f"/api/reviews/{payload['review_id']}/attest", json={"recipient_wallet": "0x" + "9a" * 20})
    assert attestation.status_code == 202
    assert attestation.json()["status"] == "confirmed"

    release = client.post(f"/api/bounties/{bounty_id}/release")
    assert release.status_code == 202
    assert client.get(f"/api/bounties/{bounty_id}").json()["status"] == "paid_out"


def test_duplicate_bounty_registration_is_rejected():
    assert create_bounty().status_code == 409
