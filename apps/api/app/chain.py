"""Minimal EVM adapter for the deployed Fair Bounty Judge contracts."""
from __future__ import annotations

import hashlib
from typing import Any

from .config import Settings

ESCROW_ABI = [
    {"type": "function", "name": "releaseBounty", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": []},
    {"type": "function", "name": "getBounty", "stateMutability": "view", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": [{"name": "", "type": "tuple", "components": [{"name": "maintainer", "type": "address"}, {"name": "token", "type": "address"}, {"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint128"}, {"name": "expiresAt", "type": "uint64"}, {"name": "releaseAt", "type": "uint64"}, {"name": "status", "type": "uint8"}]}]},
]
VERDICT_REGISTRY_ABI = [
    {"type": "function", "name": "submitVerdict", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}, {"name": "evidenceHash", "type": "bytes32"}, {"name": "evidenceCid", "type": "string"}, {"name": "recipient", "type": "address"}, {"name": "finalScoreBps", "type": "uint16"}], "outputs": []},
    {"type": "function", "name": "getVerdict", "stateMutability": "view", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": [{"name": "", "type": "tuple", "components": [{"name": "evidenceHash", "type": "bytes32"}, {"name": "evidenceCid", "type": "string"}, {"name": "recipient", "type": "address"}, {"name": "finalScoreBps", "type": "uint16"}, {"name": "submittedAt", "type": "uint64"}, {"name": "challengeEndsAt", "type": "uint64"}, {"name": "exists", "type": "bool"}]}]},
]


class ChainError(RuntimeError):
    pass


class ChainClient:
    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]: ...
    async def submit_verdict(self, bounty_id: str, evidence_hash: str, evidence_cid: str, recipient: str, final_score_bps: int) -> dict[str, Any]: ...
    async def release_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_verdict(self, bounty_id: str) -> dict[str, Any]: ...


def _bytes32(value: str, field: str) -> bytes:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) != 66:
        raise ChainError(f"{field} must be a 32-byte 0x-prefixed hex value")
    try:
        return bytes.fromhex(value[2:])
    except ValueError as exc:
        raise ChainError(f"{field} must be hexadecimal") from exc


class FixtureChainClient(ChainClient):
    def __init__(self, chain_id: int) -> None:
        self._chain_id = chain_id
        self._bounties: dict[str, dict[str, Any]] = {}
        self._verdicts: dict[str, dict[str, Any]] = {}
        self._released: set[str] = set()

    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("creation transaction hash is invalid")
        if bounty_id not in self._bounties:
            raise ChainError("Fixture chain has no matching created bounty")
        return {"transaction_hash": transaction_hash, "block_number": 1, "network": f"fixture-{self._chain_id}", "status": "confirmed"}

    async def submit_verdict(self, bounty_id: str, evidence_hash: str, evidence_cid: str, recipient: str, final_score_bps: int) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        _bytes32(evidence_hash, "evidence_hash")
        if bounty_id in self._verdicts:
            raise ChainError("A verdict has already been submitted for this bounty")
        if not evidence_cid.startswith(("Qm", "bafy")):
            raise ChainError("Evidence CID is not valid")
        if not 0 <= final_score_bps <= 10_000:
            raise ChainError("final_score_bps is outside the valid range")
        transaction_hash = "0x" + hashlib.sha256(f"verdict:{bounty_id}:{evidence_hash}:{evidence_cid}:{recipient}:{final_score_bps}".encode()).hexdigest()
        verdict = {"bounty_id": bounty_id, "evidence_hash": evidence_hash, "evidence_cid": evidence_cid, "recipient": recipient, "final_score_bps": final_score_bps, "exists": True}
        self._verdicts[bounty_id] = verdict
        return {"transaction_hash": transaction_hash, "network": f"fixture-{self._chain_id}", "status": "confirmed", "verdict": verdict}

    async def release_bounty(self, bounty_id: str) -> dict[str, Any]:
        if bounty_id not in self._verdicts:
            raise ChainError("No verdict is available for this bounty")
        if bounty_id in self._released:
            raise ChainError("Bounty has already been released")
        self._released.add(bounty_id)
        return {"transaction_hash": "0x" + hashlib.sha256(f"release:{bounty_id}".encode()).hexdigest(), "network": f"fixture-{self._chain_id}", "status": "confirmed"}

    async def get_bounty(self, bounty_id: str) -> dict[str, Any]:
        if bounty_id in self._bounties:
            return self._bounties[bounty_id]
        return {"bounty_id": bounty_id, "status": "paid_out" if bounty_id in self._released else "verdict_submitted" if bounty_id in self._verdicts else "open"}

    async def get_verdict(self, bounty_id: str) -> dict[str, Any]:
        return self._verdicts.get(bounty_id, {"bounty_id": bounty_id, "exists": False})


class Web3ChainClient(ChainClient):
    def __init__(self, settings: Settings) -> None:
        if not all((settings.amoy_rpc_url, settings.bounty_escrow_address, settings.verdict_registry_address, settings.relayer_private_key)):
            raise ChainError("Chain RPC, contract addresses, and relayer key must be configured")
        try:
            from web3 import Web3
        except ImportError as exc:
            raise ChainError("web3 is required for non-fixture chain access") from exc
        self._web3 = Web3(Web3.HTTPProvider(settings.amoy_rpc_url))
        if not self._web3.is_connected():
            raise ChainError("Unable to connect to the configured EVM RPC endpoint")
        self._chain_id = settings.chain_id
        self._account = self._web3.eth.account.from_key(settings.relayer_private_key.get_secret_value())
        self._escrow = self._web3.eth.contract(address=self._web3.to_checksum_address(settings.bounty_escrow_address), abi=ESCROW_ABI)
        self._registry = self._web3.eth.contract(address=self._web3.to_checksum_address(settings.verdict_registry_address), abi=VERDICT_REGISTRY_ABI)

    def _transact(self, call: Any) -> dict[str, Any]:
        nonce = self._web3.eth.get_transaction_count(self._account.address, "pending")
        transaction = call.build_transaction({"from": self._account.address, "nonce": nonce, "chainId": self._chain_id, "gasPrice": self._web3.eth.gas_price})
        transaction["gas"] = self._web3.eth.estimate_gas(transaction)
        signed = self._account.sign_transaction(transaction)
        raw_transaction = getattr(signed, "raw_transaction", getattr(signed, "rawTransaction", None))
        transaction_hash = self._web3.eth.send_raw_transaction(raw_transaction)
        receipt = self._web3.eth.wait_for_transaction_receipt(transaction_hash, timeout=120)
        if receipt.status != 1:
            raise ChainError("EVM transaction reverted")
        return {"transaction_hash": transaction_hash.hex(), "network": str(self._chain_id), "status": "confirmed", "block_number": receipt.blockNumber}

    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if not isinstance(transaction_hash, str) or not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("creation transaction hash is invalid")
        try:
            receipt = self._web3.eth.get_transaction_receipt(transaction_hash)
        except Exception as exc:
            raise ChainError("creation transaction was not found or is not confirmed") from exc
        if receipt.status != 1:
            raise ChainError("creation transaction reverted")
        if not receipt.to or receipt.to.lower() != self._escrow.address.lower():
            raise ChainError("creation transaction was not sent to the configured escrow")
        try:
            events = self._escrow.events.BountyCreated().process_receipt(receipt)
        except Exception as exc:
            raise ChainError("creation transaction did not emit a readable BountyCreated event") from exc
        expected_id = bounty_id.lower()
        if not any(self._web3.to_hex(event["args"]["bountyId"]).lower() == expected_id for event in events):
            raise ChainError("creation transaction did not create the requested bounty")
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "network": str(self._chain_id),
            "status": "confirmed",
        }

    async def submit_verdict(self, bounty_id: str, evidence_hash: str, evidence_cid: str, recipient: str, final_score_bps: int) -> dict[str, Any]:
        call = self._registry.functions.submitVerdict(_bytes32(bounty_id, "bounty_id"), _bytes32(evidence_hash, "evidence_hash"), evidence_cid, self._web3.to_checksum_address(recipient), final_score_bps)
        return self._transact(call)

    async def release_bounty(self, bounty_id: str) -> dict[str, Any]:
        return self._transact(self._escrow.functions.releaseBounty(_bytes32(bounty_id, "bounty_id")))

    async def get_bounty(self, bounty_id: str) -> dict[str, Any]:
        values = self._escrow.functions.getBounty(_bytes32(bounty_id, "bounty_id")).call()
        keys = ("maintainer", "token", "recipient", "amount", "expires_at", "release_at", "status")
        return dict(zip(keys, values, strict=True))

    async def get_verdict(self, bounty_id: str) -> dict[str, Any]:
        values = self._registry.functions.getVerdict(_bytes32(bounty_id, "bounty_id")).call()
        keys = ("evidence_hash", "evidence_cid", "recipient", "final_score_bps", "submitted_at", "challenge_ends_at", "exists")
        return dict(zip(keys, values, strict=True))


def build_chain_client(settings: Settings) -> ChainClient:
    if settings.fixture_mode:
        return FixtureChainClient(settings.chain_id)
    return Web3ChainClient(settings)
