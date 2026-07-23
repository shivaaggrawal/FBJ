"""Run the complete local bounty-to-payout demo without POL or external credentials."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from time import time
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings
from app.main import app


def require_success(response):
    if response.is_success:
        return response.json()
    raise RuntimeError(f"{response.request.method} {response.request.url.path} failed: {response.status_code} {response.text}")


def main() -> None:
    settings = Settings()
    if not settings.fixture_mode:
        raise RuntimeError("Fixture demo requires FIXTURE_MODE=true")
    repository = settings.github_allowed_repositories[0] if settings.github_allowed_repositories else "owner/demo-repository"
    bounty_id = "0x" + uuid4().hex * 2

    with TestClient(app) as client:
        require_success(client.post("/api/bounties", json={
            "contract_bounty_id": bounty_id,
            "repository": repository,
            "issue_url": f"https://github.com/{repository}/issues/1",
            "reward_token": "0x" + "12" * 20,
            "reward_amount": "1000000",
            "maintainer_wallet": "0x" + "34" * 20,
            "expires_at": int(time()) + 86_400,
            "challenge_seconds": 3600,
        }))
        review = require_success(client.post("/api/reviews/fixture", json={
            "bounty_id": bounty_id,
            "repository": repository,
            "pull_request_number": 1,
            "commit_sha": "a" * 40,
            "title": "Fixture demo change",
            "diff": "diff --git a/demo.py b/demo.py\n+print('ready')",
            "changed_files": [{"path": "demo.py", "additions": 1, "deletions": 0}],
            "author": "demo-contributor",
        }))
        attestation = require_success(client.post(
            f"/api/reviews/{review['review_id']}/attest",
            json={"recipient_wallet": "0x" + "56" * 20},
        ))
        release = require_success(client.post(f"/api/bounties/{bounty_id}/release"))
        bounty = require_success(client.get(f"/api/bounties/{bounty_id}"))

    print(json.dumps({
        "bountyId": bounty_id,
        "reviewId": review["review_id"],
        "evidenceCid": review["evidence_cid"],
        "evidenceHash": review["evidence_hash"],
        "attestationTransaction": attestation["transaction_hash"],
        "releaseTransaction": release["transaction_hash"],
        "bountyStatus": bounty["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
