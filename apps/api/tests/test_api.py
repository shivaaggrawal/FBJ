import hashlib
import hmac

from eth_account import Account
from eth_account.messages import encode_defunct
from app.schemas import BountyResponse
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app

client = TestClient(app)
settings = Settings()
repository = settings.github_allowed_repositories[0] if settings.github_allowed_repositories else "owner/demo-repository"
webhook_secret = settings.github_webhook_secret.get_secret_value()


class FakeGitHubClient:
    def __init__(self, settings: Settings, installation_id: str | int | None = None) -> None:
        self.installation_id = installation_id

    async def create_pending_check(self, repository: str, commit_sha: str) -> int:
        return 101

    async def fetch_review_input(self, bounty_id: str, repository: str, number: int, criteria: str):
        from app.schemas import ReviewInput

        return ReviewInput(
            bounty_id=bounty_id,
            repository=repository,
            pull_request_number=number,
            commit_sha="a" * 40,
            title="Test",
            diff="diff --git a/a.py b/a.py",
            changed_files=[],
            author="developer",
            criteria=criteria,
        )

    async def complete_check(self, repository: str, check_run_id: int, result) -> None:
        return None


def create_bounty(issue_number: int, marker: str):
    return client.post("/api/bounties", json={"contract_bounty_id": "0x" + marker * 32, "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/{issue_number}", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})


CLAIM_CODE = "a1" * 16


def claim_bounty(contract_bounty_id: str, github_login: str = "developer"):
    contributor = Account.create()
    claim = {"contributor_wallet": contributor.address, "contributor_github_login": github_login, "claim_code": CLAIM_CODE}
    message = client.post(f"/api/bounties/{contract_bounty_id}/claim-message", json=claim)
    assert message.status_code == 200
    claim["claim_signature"] = contributor.sign_message(encode_defunct(text=message.json()["message"])).signature.hex()
    response = client.post(f"/api/bounties/{contract_bounty_id}/claim", json=claim)
    assert response.status_code == 200
    return response


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


def test_client_config_uses_isolated_fixture_settings():
    response = client.get("/api/client-config")
    assert response.status_code == 200
    assert response.json() == {
        "chain_id": 31337,
        "chain_hex": "0x7a69",
        "chain_name": "Hardhat Local",
        "explorer_base_url": None,
        "fixture_mode": True,
        "reward_token_address": None,
        "wallet_network": {
            "chainId": "0x7a69",
            "chainName": "Hardhat Local",
            "rpcUrls": ["http://127.0.0.1:8545"],
            "nativeCurrency": {"name": "Hardhat ETH", "symbol": "ETH", "decimals": 18},
        },
    }


def test_dashboard_is_served_by_the_api():
    response = client.get("/app/")
    assert response.status_code == 200
    assert "Fair Bounty Judge" in response.text


def test_bounty_can_be_created_without_a_recipient_before_a_contributor_claims_it():
    response = client.post("/api/bounties/prepare", json={
        "contract_bounty_id": "0x" + "ef" * 32,
        "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/recipient-required",
        "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000",
        "maintainer_wallet": "0x" + "34" * 20,
        "expires_at": 1_900_000_000,
        "challenge_seconds": 3600,
    })
    assert response.status_code == 200


def test_signed_claim_locks_the_contributor_wallet_and_prevents_a_second_active_claim():
    bounty_id = "0x" + "d4" * 32
    assert create_bounty(4, "d4").status_code == 201
    claimed = claim_bounty(bounty_id).json()
    assert claimed["status"] == "claimed"
    assert claimed["recipient_wallet"] == claimed["contributor_wallet"]
    assert claimed["contributor_github_login"] == "developer"
    assert claimed["claim_expires_at"] > 0

    attacker = Account.create()
    payload = {"contributor_wallet": attacker.address, "contributor_github_login": "attacker", "claim_code": "b2" * 16}
    message = client.post(f"/api/bounties/{bounty_id}/claim-message", json=payload).json()["message"]
    payload["claim_signature"] = attacker.sign_message(encode_defunct(text=message)).signature.hex()
    response = client.post(f"/api/bounties/{bounty_id}/claim", json=payload)
    assert response.status_code == 409


def test_legacy_bounty_response_without_recipient_is_displayable():
    legacy = BountyResponse.model_validate({
        "id": "legacy-bounty",
        "contract_bounty_id": "0x" + "aa" * 32,
        "repository": "owner/legacy-repository",
        "issue_url": "https://github.com/owner/legacy-repository/issues/1",
        "criteria": "",
        "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000",
        "maintainer_wallet": "0x" + "34" * 20,
        "expires_at": 1_900_000_000,
        "challenge_seconds": 3600,
        "status": "paid_out",
    })
    assert legacy.recipient_wallet is None


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
    payload = (f'{{"action":"opened","number":1,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","body":"Fixes #404","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={
        "X-Hub-Signature-256": "sha256=" + signature,
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": "no-bounty-delivery",
    })
    assert response.status_code == 202
    assert response.json()["status"] == "no_matching_claimed_bounty"


def test_valid_supported_webhook_is_accepted(monkeypatch):
    monkeypatch.setattr("app.main.GitHubAppClient", FakeGitHubClient)
    monkeypatch.setattr("app.worker.GitHubAppClient", FakeGitHubClient)
    bounty_id = "0x" + "ab" * 32
    assert create_bounty(1, "ab").status_code == 201
    claim_bounty(bounty_id)
    payload = (f'{{"action":"opened","number":1,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","body":"Fixes #1\\nFBJ-CLAIM:{CLAIM_CODE}","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "delivery-1"})
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_webhook_rejects_a_pull_request_from_an_unclaimed_github_account():
    bounty_id = "0x" + "e5" * 32
    assert create_bounty(5, "e5").status_code == 201
    claim_bounty(bounty_id, github_login="developer")
    payload = (f'{{"action":"opened","number":5,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","body":"Fixes #5\\nFBJ-CLAIM:{CLAIM_CODE}","user":{{"login":"someone-else"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "claimant-mismatch-delivery"})
    assert response.status_code == 202
    assert response.json()["status"] == "claimant_mismatch"


def test_edited_pull_request_with_a_bounty_reference_is_accepted(monkeypatch):
    monkeypatch.setattr("app.main.GitHubAppClient", FakeGitHubClient)
    monkeypatch.setattr("app.worker.GitHubAppClient", FakeGitHubClient)
    bounty_id = "0x" + "bc" * 32
    assert create_bounty(3, "bc").status_code == 201
    claim_bounty(bounty_id)
    payload = (f'{{"action":"edited","number":3,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}},"title":"Test","body":"Fixes #3\\nFBJ-CLAIM:{CLAIM_CODE}","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "edited-delivery"})
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_pr_description_edit_triggers_a_matching_bounty_review(monkeypatch):
    monkeypatch.setattr("app.main.GitHubAppClient", FakeGitHubClient)
    monkeypatch.setattr("app.worker.GitHubAppClient", FakeGitHubClient)
    bounty_id = "0x" + "ac" * 32
    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/2", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20,
        "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert bounty.status_code == 201
    payload = (f'{{"action":"edited","number":3,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}},"title":"Test","body":"Closes #2","user":{{"login":"developer"}}}}}}').encode()
    signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    response = client.post("/webhooks/github", content=payload, headers={"X-Hub-Signature-256": "sha256=" + signature, "X-GitHub-Event": "pull_request", "X-GitHub-Delivery": "edited-description-delivery"})
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_duplicate_delivery_is_idempotent(monkeypatch):
    monkeypatch.setattr("app.main.GitHubAppClient", FakeGitHubClient)
    monkeypatch.setattr("app.worker.GitHubAppClient", FakeGitHubClient)
    bounty_id = "0x" + "ce" * 32
    assert create_bounty(2, "ce").status_code == 201
    claim_bounty(bounty_id)
    payload = (f'{{"action":"opened","number":2,"repository":{{"full_name":"{repository}"}},"pull_request":{{"head":{{"sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}},"title":"Test","body":"Fixes #2\\nFBJ-CLAIM:{CLAIM_CODE}","user":{{"login":"developer"}}}}}}').encode()
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
    assert create_bounty(1, "ab").status_code == 409


def test_wallet_preparation_endpoints_return_unsigned_actions():
    bounty_id = "0x" + "ef" * 32
    create = client.post("/api/bounties/prepare", json={"contract_bounty_id": bounty_id, "repository": repository,
        "issue_url": f"https://github.com/{repository}/issues/3", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
    assert create.status_code == 200
    assert create.json()["transaction"]["approval"]["operation"] == "approve"

    bounty = client.post("/api/bounties", json={"contract_bounty_id": bounty_id, "repository": "owner/dispute-demo",
        "issue_url": "https://github.com/owner/dispute-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
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
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600})
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
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600}).status_code == 201
    cancelled = client.post(f"/api/bounties/{cancelled_bounty}/cancel/confirm", json={"transaction_hash": "0x" + "33" * 32})
    assert cancelled.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{cancelled_bounty}").json()["status"] == "cancelled"

    refunded_bounty = "0x" + "fc" * 32
    assert client.post("/api/bounties", json={"contract_bounty_id": refunded_bounty, "repository": "owner/refund-demo",
        "issue_url": "https://github.com/owner/refund-demo/issues/1", "reward_token": "0x" + "12" * 20,
        "reward_amount": "1000000", "maintainer_wallet": "0x" + "34" * 20, "recipient_wallet": "0x" + "56" * 20, "expires_at": 1_900_000_000, "challenge_seconds": 3600}).status_code == 201
    refunded = client.post(f"/api/bounties/{refunded_bounty}/refund/confirm", json={"transaction_hash": "0x" + "44" * 32})
    assert refunded.json()["status"] == "confirmed"
    assert client.get(f"/api/bounties/{refunded_bounty}").json()["status"] == "refunded"
