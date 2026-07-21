"""Content-addressed evidence storage used before a verdict is published on-chain."""
from __future__ import annotations

import hashlib

import httpx

from .config import Settings

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class IpfsError(RuntimeError):
    pass


class IpfsClient:
    async def pin_bytes(self, evidence_bytes: bytes) -> str: ...
    async def fetch_bytes(self, cid: str) -> bytes: ...


def _base58_encode(value: bytes) -> str:
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = _BASE58_ALPHABET[remainder] + encoded
    prefix = "1" * (len(value) - len(value.lstrip(b"\0")))
    return prefix + (encoded or "1")


def fixture_cid(evidence_bytes: bytes) -> str:
    """Produce a valid CIDv0-style multihash for deterministic local workflows."""
    return _base58_encode(b"\x12\x20" + hashlib.sha256(evidence_bytes).digest())


class FixtureIpfsClient(IpfsClient):
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def pin_bytes(self, evidence_bytes: bytes) -> str:
        cid = fixture_cid(evidence_bytes)
        self._objects[cid] = evidence_bytes
        return cid

    async def fetch_bytes(self, cid: str) -> bytes:
        try:
            return self._objects[cid]
        except KeyError as exc:
            raise IpfsError("Evidence CID is not available in fixture storage") from exc


class PinataIpfsClient(IpfsClient):
    def __init__(self, settings: Settings) -> None:
        if settings.pinata_jwt is None:
            raise IpfsError("PINATA_JWT is required for Pinata uploads")
        self._jwt = settings.pinata_jwt.get_secret_value()
        self._api_url = settings.pinata_api_url
        self._gateway_url = settings.ipfs_gateway_url.rstrip("/")

    async def pin_bytes(self, evidence_bytes: bytes) -> str:
        headers = {"Authorization": f"Bearer {self._jwt}"}
        files = {"file": ("fair-bounty-evidence.json", evidence_bytes, "application/json")}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._api_url, headers=headers, files=files)
        if response.is_error:
            raise IpfsError(f"Pinata upload failed with HTTP {response.status_code}")
        cid = response.json().get("IpfsHash")
        if not isinstance(cid, str) or not cid:
            raise IpfsError("Pinata upload response did not include IpfsHash")
        return cid

    async def fetch_bytes(self, cid: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self._gateway_url}/{cid}")
        if response.is_error:
            raise IpfsError(f"IPFS gateway returned HTTP {response.status_code}")
        return response.content


def build_ipfs_client(settings: Settings) -> IpfsClient:
    if settings.ipfs_provider == "fixture":
        return FixtureIpfsClient()
    if settings.ipfs_provider == "pinata":
        return PinataIpfsClient(settings)
    raise IpfsError("IPFS_PROVIDER must be either fixture or pinata")
