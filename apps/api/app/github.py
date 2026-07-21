"""Minimal GitHub App client for PR retrieval and Checks publishing."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

from .config import Settings
from .schemas import ChangedFile, ReviewInput, ReviewResponse

_API_URL = "https://api.github.com"


class GitHubAppClient:
    def __init__(self, settings: Settings, installation_id: str | int | None = None) -> None:
        if not settings.github_app_enabled:
            raise RuntimeError("GitHub App credentials are not fully configured")
        self.installation_id = str(installation_id or settings.github_installation_id or "")
        if not self.installation_id:
            raise RuntimeError("GitHub installation ID is not configured")
        self.settings = settings

    def _app_jwt(self) -> str:
        private_key = base64.b64decode(self.settings.github_app_private_key_b64.get_secret_value()).decode("utf-8")  # type: ignore[union-attr]
        now = datetime.now(timezone.utc)
        return jwt.encode({"iat": now - timedelta(seconds=60), "exp": now + timedelta(minutes=9), "iss": self.settings.github_app_id}, private_key, algorithm="RS256")

    async def _installation_token(self) -> str:
        headers = {"Authorization": f"Bearer {self._app_jwt()}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{_API_URL}/app/installations/{self.installation_id}/access_tokens", headers=headers)
            response.raise_for_status()
        return response.json()["token"]

    async def _request(self, method: str, path: str, *, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None) -> httpx.Response:
        token = await self._installation_token()
        request_headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(method, f"{_API_URL}{path}", headers=request_headers, json=json)
            response.raise_for_status()
            return response

    async def fetch_review_input(self, bounty_id: str, repository: str, number: int, criteria: str) -> ReviewInput:
        pr = (await self._request("GET", f"/repos/{repository}/pulls/{number}")).json()
        files = (await self._request("GET", f"/repos/{repository}/pulls/{number}/files?per_page=100")).json()
        diff_response = await self._request("GET", f"/repos/{repository}/pulls/{number}", headers={"Accept": "application/vnd.github.diff"})
        return ReviewInput(bounty_id=bounty_id, repository=repository, pull_request_number=number, commit_sha=pr["head"]["sha"], title=pr["title"], body=pr.get("body"), diff=diff_response.text, changed_files=[ChangedFile(path=item["filename"], additions=item["additions"], deletions=item["deletions"]) for item in files], author=pr["user"]["login"], criteria=criteria)

    async def create_pending_check(self, repository: str, commit_sha: str) -> int:
        response = await self._request("POST", f"/repos/{repository}/check-runs", json={"name": self.settings.github_check_name, "head_sha": commit_sha, "status": "in_progress", "output": {"title": "Fair Bounty Judge review started", "summary": "The pull request is being evaluated by independent review agents."}})
        return int(response.json()["id"])

    async def complete_check(self, repository: str, check_run_id: int, result: ReviewResponse) -> None:
        findings = [f"- **{agent.agent.value.title()}**: {agent.score_bps / 100:.0f}% — {agent.summary}" for agent in result.agent_results]
        conclusion = "success" if result.supervisor.eligible else "neutral"
        summary = "\n".join([f"Final score: **{result.supervisor.final_score_bps / 100:.0f}%**", f"Eligible: **{'Yes' if result.supervisor.eligible else 'No'}**", *findings, f"Evidence hash: `{result.evidence_hash}`"])
        await self._request("PATCH", f"/repos/{repository}/check-runs/{check_run_id}", json={"status": "completed", "conclusion": conclusion, "output": {"title": "Fair Bounty Judge verdict", "summary": summary}})
