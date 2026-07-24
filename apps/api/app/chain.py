"""Minimal EVM adapter for the deployed Fair Bounty Judge contracts."""
from __future__ import annotations

import hashlib
from typing import Any

from .config import Settings

ESCROW_ABI = [
    {"type": "function", "name": "createBounty", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}, {"name": "token", "type": "address"}, {"name": "amount", "type": "uint128"}, {"name": "expiresAt", "type": "uint64"}], "outputs": []},
    {"type": "function", "name": "cancelOpenBounty", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": []},
    {"type": "function", "name": "refundExpiredBounty", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": []},
    {"type": "function", "name": "releaseBounty", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": []},
    {"type": "function", "name": "defaultRewardToken", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "address"}]},
    {"type": "function", "name": "getBounty", "stateMutability": "view", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": [{"name": "", "type": "tuple", "components": [{"name": "maintainer", "type": "address"}, {"name": "token", "type": "address"}, {"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint128"}, {"name": "expiresAt", "type": "uint64"}, {"name": "releaseAt", "type": "uint64"}, {"name": "status", "type": "uint8"}]}]},
    {"type": "event", "name": "BountyCreated", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "maintainer", "type": "address", "indexed": True}, {"name": "token", "type": "address", "indexed": True}, {"name": "amount", "type": "uint256", "indexed": False}, {"name": "expiresAt", "type": "uint64", "indexed": False}]},
    {"type": "event", "name": "VerdictRecorded", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "recipient", "type": "address", "indexed": True}, {"name": "releaseAt", "type": "uint64", "indexed": False}]},
    {"type": "event", "name": "BountyChallenged", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}]},
    {"type": "event", "name": "BountyPaid", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "recipient", "type": "address", "indexed": True}, {"name": "amount", "type": "uint256", "indexed": False}]},
    {"type": "event", "name": "BountyRefunded", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "maintainer", "type": "address", "indexed": True}, {"name": "amount", "type": "uint256", "indexed": False}, {"name": "status", "type": "uint8", "indexed": False}]},
]
VERDICT_REGISTRY_ABI = [
    {"type": "function", "name": "submitVerdict", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}, {"name": "evidenceHash", "type": "bytes32"}, {"name": "evidenceCid", "type": "string"}, {"name": "recipient", "type": "address"}, {"name": "finalScoreBps", "type": "uint16"}], "outputs": []},
    {"type": "function", "name": "getVerdict", "stateMutability": "view", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": [{"name": "", "type": "tuple", "components": [{"name": "evidenceHash", "type": "bytes32"}, {"name": "evidenceCid", "type": "string"}, {"name": "recipient", "type": "address"}, {"name": "finalScoreBps", "type": "uint16"}, {"name": "submittedAt", "type": "uint64"}, {"name": "challengeEndsAt", "type": "uint64"}, {"name": "exists", "type": "bool"}]}]},
    {"type": "event", "name": "VerdictSubmitted", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "evidenceHash", "type": "bytes32", "indexed": False}, {"name": "recipient", "type": "address", "indexed": True}, {"name": "evidenceCid", "type": "string", "indexed": False}, {"name": "finalScoreBps", "type": "uint16", "indexed": False}, {"name": "challengeEndsAt", "type": "uint64", "indexed": False}]},
]
DISPUTE_MANAGER_ABI = [
    {"type": "function", "name": "openDispute", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}, {"name": "evidenceCid", "type": "string"}], "outputs": []},
    {"type": "function", "name": "resolveDispute", "stateMutability": "nonpayable", "inputs": [{"name": "bountyId", "type": "bytes32"}, {"name": "resolution", "type": "uint8"}], "outputs": []},
    {"type": "function", "name": "getDispute", "stateMutability": "view", "inputs": [{"name": "bountyId", "type": "bytes32"}], "outputs": [{"name": "", "type": "tuple", "components": [{"name": "challenger", "type": "address"}, {"name": "evidenceCid", "type": "string"}, {"name": "openedAt", "type": "uint64"}, {"name": "open", "type": "bool"}, {"name": "resolution", "type": "uint8"}]}]},
    {"type": "event", "name": "DisputeOpened", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "challenger", "type": "address", "indexed": True}, {"name": "evidenceCid", "type": "string", "indexed": False}]},
    {"type": "event", "name": "DisputeResolved", "anonymous": False, "inputs": [{"name": "bountyId", "type": "bytes32", "indexed": True}, {"name": "resolution", "type": "uint8", "indexed": False}, {"name": "resolver", "type": "address", "indexed": True}]},
]
ERC20_ABI = [
    {"type": "function", "name": "approve", "stateMutability": "nonpayable", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]},
]


class ChainError(RuntimeError):
    pass


class ChainClient:
    async def prepare_bounty_creation(self, bounty_id: str, token: str, amount: int, expires_at: int) -> dict[str, Any]: ...
    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]: ...
    async def prepare_open_dispute(self, bounty_id: str, evidence_cid: str) -> dict[str, Any]: ...
    async def prepare_cancel_open_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def prepare_refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def prepare_dispute_resolution(self, bounty_id: str, resolution: int) -> dict[str, Any]: ...
    async def confirm_open_dispute(self, bounty_id: str, evidence_cid: str, transaction_hash: str) -> dict[str, Any]: ...
    async def confirm_dispute_resolution(self, bounty_id: str, resolution: int, transaction_hash: str) -> dict[str, Any]: ...
    async def confirm_cancel_open_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]: ...
    async def confirm_refund_expired_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]: ...
    async def get_transaction_status(self, transaction_hash: str) -> dict[str, Any]: ...
    async def submit_verdict(self, bounty_id: str, evidence_hash: str, evidence_cid: str, recipient: str, final_score_bps: int) -> dict[str, Any]: ...
    async def release_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def resolve_dispute(self, bounty_id: str, resolution: int) -> dict[str, Any]: ...
    async def refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_bounty(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_verdict(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_dispute(self, bounty_id: str) -> dict[str, Any]: ...
    async def get_latest_block(self) -> int: ...
    async def list_events(self, from_block: int, to_block: int | None = None) -> list[dict[str, Any]]: ...


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
        self._disputes: dict[str, dict[str, Any]] = {}
        self._transaction_statuses: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def _wallet_transaction(self, operation: str) -> dict[str, Any]:
        return {"operation": operation, "chain_id": self._chain_id, "to": "fixture", "data": "fixture", "value": "0x0"}

    def _confirmed_transaction(self, transaction_hash: str) -> dict[str, Any]:
        if not isinstance(transaction_hash, str) or not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("transaction hash is invalid")
        result = {"transaction_hash": transaction_hash.lower(), "network": f"fixture-{self._chain_id}", "status": "confirmed", "block_number": 1}
        self._transaction_statuses[transaction_hash.lower()] = result
        return result

    def _append_event(self, name: str, contract: str, transaction_hash: str, args: dict[str, Any]) -> None:
        self._events.append({"event": name, "contract": contract, "block_number": 1, "transaction_hash": transaction_hash, "log_index": len(self._events), "args": args})

    async def prepare_bounty_creation(self, bounty_id: str, token: str, amount: int, expires_at: int) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if amount <= 0 or expires_at <= 0:
            raise ChainError("amount and expires_at must be positive")
        return {"approval": self._wallet_transaction("approve"), "create": self._wallet_transaction("create_bounty")}

    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("creation transaction hash is invalid")
        if bounty_id not in self._bounties:
            raise ChainError("Fixture chain has no matching created bounty")
        return {"transaction_hash": transaction_hash, "block_number": 1, "network": f"fixture-{self._chain_id}", "status": "confirmed"}

    async def prepare_open_dispute(self, bounty_id: str, evidence_cid: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if not evidence_cid.startswith(("Qm", "bafy")):
            raise ChainError("Evidence CID is not valid")
        return self._wallet_transaction("open_dispute")

    async def prepare_cancel_open_bounty(self, bounty_id: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        return self._wallet_transaction("cancel_open_bounty")

    async def prepare_refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        return self._wallet_transaction("refund_expired_bounty")

    async def prepare_dispute_resolution(self, bounty_id: str, resolution: int) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if resolution not in {1, 2}:
            raise ChainError("resolution must be 1 (pay recipient) or 2 (refund maintainer)")
        return self._wallet_transaction("resolve_dispute")

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
        self._append_event("VerdictSubmitted", "verdict_registry", transaction_hash, verdict)
        return {"transaction_hash": transaction_hash, "network": f"fixture-{self._chain_id}", "status": "confirmed", "verdict": verdict}

    async def release_bounty(self, bounty_id: str) -> dict[str, Any]:
        if bounty_id not in self._verdicts:
            raise ChainError("No verdict is available for this bounty")
        if bounty_id in self._released:
            raise ChainError("Bounty has already been released")
        self._released.add(bounty_id)
        transaction_hash = "0x" + hashlib.sha256(f"release:{bounty_id}".encode()).hexdigest()
        self._append_event("BountyPaid", "bounty_escrow", transaction_hash, {"bounty_id": bounty_id})
        return {"transaction_hash": transaction_hash, "network": f"fixture-{self._chain_id}", "status": "confirmed"}

    async def confirm_open_dispute(self, bounty_id: str, evidence_cid: str, transaction_hash: str) -> dict[str, Any]:
        await self.prepare_open_dispute(bounty_id, evidence_cid)
        if bounty_id in self._disputes:
            raise ChainError("A dispute has already been opened for this bounty")
        result = self._confirmed_transaction(transaction_hash)
        dispute = {"challenger": "fixture-wallet", "evidence_cid": evidence_cid, "opened_at": 1, "open": True, "resolution": 0}
        self._disputes[bounty_id] = dispute
        self._append_event("BountyChallenged", "bounty_escrow", transaction_hash, {"bounty_id": bounty_id})
        self._append_event("DisputeOpened", "dispute_manager", transaction_hash, {"bounty_id": bounty_id, **dispute})
        return result

    async def confirm_dispute_resolution(self, bounty_id: str, resolution: int, transaction_hash: str) -> dict[str, Any]:
        await self.prepare_dispute_resolution(bounty_id, resolution)
        dispute = self._disputes.get(bounty_id)
        if dispute is None or not dispute["open"]:
            raise ChainError("No open dispute exists for this bounty")
        result = self._confirmed_transaction(transaction_hash)
        dispute["open"] = False
        dispute["resolution"] = resolution
        self._append_event("BountyPaid" if resolution == 1 else "BountyRefunded", "bounty_escrow", transaction_hash, {"bounty_id": bounty_id, "status": 7})
        self._append_event("DisputeResolved", "dispute_manager", transaction_hash, {"bounty_id": bounty_id, "resolution": resolution, "resolver": "fixture-resolver"})
        return result

    async def confirm_cancel_open_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        await self.prepare_cancel_open_bounty(bounty_id)
        result = self._confirmed_transaction(transaction_hash)
        self._append_event("BountyRefunded", "bounty_escrow", transaction_hash, {"bounty_id": bounty_id, "status": 6})
        return result

    async def confirm_refund_expired_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        await self.prepare_refund_expired_bounty(bounty_id)
        result = self._confirmed_transaction(transaction_hash)
        self._append_event("BountyRefunded", "bounty_escrow", transaction_hash, {"bounty_id": bounty_id, "status": 7})
        return result

    async def resolve_dispute(self, bounty_id: str, resolution: int) -> dict[str, Any]:
        transaction_hash = "0x" + hashlib.sha256(f"resolve:{bounty_id}:{resolution}".encode()).hexdigest()
        return await self.confirm_dispute_resolution(bounty_id, resolution, transaction_hash)

    async def refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]:
        transaction_hash = "0x" + hashlib.sha256(f"refund:{bounty_id}".encode()).hexdigest()
        return await self.confirm_refund_expired_bounty(bounty_id, transaction_hash)

    async def get_bounty(self, bounty_id: str) -> dict[str, Any]:
        if bounty_id in self._bounties:
            return self._bounties[bounty_id]
        return {"bounty_id": bounty_id, "status": "paid_out" if bounty_id in self._released else "verdict_submitted" if bounty_id in self._verdicts else "open"}

    async def get_verdict(self, bounty_id: str) -> dict[str, Any]:
        return self._verdicts.get(bounty_id, {"bounty_id": bounty_id, "exists": False})

    async def get_dispute(self, bounty_id: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        return self._disputes.get(bounty_id, {"challenger": "0x0000000000000000000000000000000000000000", "evidence_cid": "", "opened_at": 0, "open": False, "resolution": 0})

    async def get_transaction_status(self, transaction_hash: str) -> dict[str, Any]:
        result = self._transaction_statuses.get(transaction_hash.lower())
        if result is not None:
            return result
        if not isinstance(transaction_hash, str) or not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("transaction hash is invalid")
        return {"transaction_hash": transaction_hash.lower(), "network": f"fixture-{self._chain_id}", "status": "pending"}

    async def get_latest_block(self) -> int:
        return 1

    async def list_events(self, from_block: int, to_block: int | None = None) -> list[dict[str, Any]]:
        if from_block < 0 or (to_block is not None and to_block < from_block):
            raise ChainError("Invalid block range")
        return [event for event in self._events if event["block_number"] >= from_block and (to_block is None or event["block_number"] <= to_block)]


class Web3ChainClient(ChainClient):
    def __init__(self, settings: Settings) -> None:
        if not all((settings.amoy_rpc_url, settings.bounty_escrow_address, settings.verdict_registry_address, settings.dispute_manager_address, settings.relayer_private_key)):
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
        self._resolver_account = self._web3.eth.account.from_key(settings.dispute_resolver_private_key.get_secret_value()) if settings.dispute_resolver_private_key else None
        self._escrow = self._web3.eth.contract(address=self._web3.to_checksum_address(settings.bounty_escrow_address), abi=ESCROW_ABI)
        self._registry = self._web3.eth.contract(address=self._web3.to_checksum_address(settings.verdict_registry_address), abi=VERDICT_REGISTRY_ABI)
        self._disputes = self._web3.eth.contract(address=self._web3.to_checksum_address(settings.dispute_manager_address), abi=DISPUTE_MANAGER_ABI)

    def _transact(self, call: Any, account: Any | None = None) -> dict[str, Any]:
        try:
            sender = account or self._account
            nonce = self._web3.eth.get_transaction_count(sender.address, "pending")
            transaction = call.build_transaction({"from": sender.address, "nonce": nonce, "chainId": self._chain_id, "gasPrice": self._web3.eth.gas_price})
            transaction["gas"] = self._web3.eth.estimate_gas(transaction)
            signed = sender.sign_transaction(transaction)
            raw_transaction = getattr(signed, "raw_transaction", getattr(signed, "rawTransaction", None))
            transaction_hash = self._web3.eth.send_raw_transaction(raw_transaction)
            receipt = self._web3.eth.wait_for_transaction_receipt(transaction_hash, timeout=120)
        except Exception as exc:
            raise ChainError("Could not submit or confirm the EVM transaction") from exc
        if receipt.status != 1:
            raise ChainError("EVM transaction reverted")
        return {"transaction_hash": transaction_hash.hex(), "network": str(self._chain_id), "status": "confirmed", "block_number": receipt.blockNumber}

    def _receipt_status(self, transaction_hash: str) -> tuple[dict[str, Any], Any | None]:
        if not isinstance(transaction_hash, str) or not transaction_hash.startswith("0x") or len(transaction_hash) != 66:
            raise ChainError("transaction hash is invalid")
        try:
            receipt = self._web3.eth.get_transaction_receipt(transaction_hash)
        except Exception as exc:
            if exc.__class__.__name__ == "TransactionNotFound":
                return ({"transaction_hash": transaction_hash.lower(), "network": str(self._chain_id), "status": "pending"}, None)
            raise ChainError("Could not retrieve the EVM transaction receipt") from exc
        if receipt is None:
            return ({"transaction_hash": transaction_hash.lower(), "network": str(self._chain_id), "status": "pending"}, None)
        if receipt.status != 1:
            return ({"transaction_hash": receipt.transactionHash.hex(), "network": str(self._chain_id), "status": "failed", "error": "EVM transaction reverted", "block_number": receipt.blockNumber}, receipt)
        return ({"transaction_hash": receipt.transactionHash.hex(), "network": str(self._chain_id), "status": "confirmed", "block_number": receipt.blockNumber}, receipt)

    def _confirmed_event(self, contract: Any, event_name: str, bounty_id: str, receipt: Any, expected: dict[str, Any] | None = None) -> None:
        if not receipt.to or receipt.to.lower() != contract.address.lower():
            raise ChainError("transaction was sent to the wrong contract")
        try:
            events = getattr(contract.events, event_name)().process_receipt(receipt)
        except Exception as exc:
            raise ChainError(f"transaction did not emit a readable {event_name} event") from exc
        bounty_id_bytes = _bytes32(bounty_id, "bounty_id")
        for event in events:
            args = event["args"]
            if args.get("bountyId") != bounty_id_bytes:
                continue
            if all(args.get(key) == value for key, value in (expected or {}).items()):
                return
        raise ChainError(f"transaction did not emit the expected {event_name} event")

    def _wallet_transaction(self, contract: Any, function: str, arguments: list[Any]) -> dict[str, Any]:
        return {"to": contract.address, "data": contract.encode_abi(function, args=arguments), "value": "0x0", "chain_id": self._chain_id}

    async def prepare_bounty_creation(self, bounty_id: str, token: str, amount: int, expires_at: int) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if amount <= 0 or expires_at <= 0:
            raise ChainError("amount and expires_at must be positive")
        requested_token = self._web3.to_checksum_address(token)
        reward_token = self._escrow.functions.defaultRewardToken().call() if int(requested_token, 16) == 0 else requested_token
        return {
            "approval": self._wallet_transaction(self._web3.eth.contract(address=reward_token, abi=ERC20_ABI), "approve", [self._escrow.address, amount]),
            "create": self._wallet_transaction(self._escrow, "createBounty", [_bytes32(bounty_id, "bounty_id"), requested_token, amount, expires_at]),
            "token": reward_token,
        }

    async def prepare_open_dispute(self, bounty_id: str, evidence_cid: str) -> dict[str, Any]:
        _bytes32(bounty_id, "bounty_id")
        if not evidence_cid.startswith(("Qm", "bafy")):
            raise ChainError("Evidence CID is not valid")
        return self._wallet_transaction(self._disputes, "openDispute", [_bytes32(bounty_id, "bounty_id"), evidence_cid])

    async def prepare_cancel_open_bounty(self, bounty_id: str) -> dict[str, Any]:
        return self._wallet_transaction(self._escrow, "cancelOpenBounty", [_bytes32(bounty_id, "bounty_id")])

    async def prepare_refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]:
        return self._wallet_transaction(self._escrow, "refundExpiredBounty", [_bytes32(bounty_id, "bounty_id")])

    async def prepare_dispute_resolution(self, bounty_id: str, resolution: int) -> dict[str, Any]:
        if resolution not in {1, 2}:
            raise ChainError("resolution must be 1 (pay recipient) or 2 (refund maintainer)")
        return self._wallet_transaction(self._disputes, "resolveDispute", [_bytes32(bounty_id, "bounty_id"), resolution])

    async def confirm_open_dispute(self, bounty_id: str, evidence_cid: str, transaction_hash: str) -> dict[str, Any]:
        status, receipt = self._receipt_status(transaction_hash)
        if receipt is None or status["status"] != "confirmed":
            return status
        self._confirmed_event(self._disputes, "DisputeOpened", bounty_id, receipt, {"evidenceCid": evidence_cid})
        return status

    async def confirm_dispute_resolution(self, bounty_id: str, resolution: int, transaction_hash: str) -> dict[str, Any]:
        if resolution not in {1, 2}:
            raise ChainError("resolution must be 1 (pay recipient) or 2 (refund maintainer)")
        status, receipt = self._receipt_status(transaction_hash)
        if receipt is None or status["status"] != "confirmed":
            return status
        self._confirmed_event(self._disputes, "DisputeResolved", bounty_id, receipt, {"resolution": resolution})
        return status

    async def confirm_cancel_open_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        status, receipt = self._receipt_status(transaction_hash)
        if receipt is None or status["status"] != "confirmed":
            return status
        self._confirmed_event(self._escrow, "BountyRefunded", bounty_id, receipt, {"status": 6})
        return status

    async def confirm_refund_expired_bounty(self, bounty_id: str, transaction_hash: str) -> dict[str, Any]:
        status, receipt = self._receipt_status(transaction_hash)
        if receipt is None or status["status"] != "confirmed":
            return status
        self._confirmed_event(self._escrow, "BountyRefunded", bounty_id, receipt, {"status": 7})
        return status

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

    async def resolve_dispute(self, bounty_id: str, resolution: int) -> dict[str, Any]:
        if self._resolver_account is None:
            raise ChainError("DISPUTE_RESOLVER_PRIVATE_KEY is required for server-side dispute resolution")
        await self.prepare_dispute_resolution(bounty_id, resolution)
        return self._transact(self._disputes.functions.resolveDispute(_bytes32(bounty_id, "bounty_id"), resolution), self._resolver_account)

    async def refund_expired_bounty(self, bounty_id: str) -> dict[str, Any]:
        return self._transact(self._escrow.functions.refundExpiredBounty(_bytes32(bounty_id, "bounty_id")))

    async def get_bounty(self, bounty_id: str) -> dict[str, Any]:
        values = self._escrow.functions.getBounty(_bytes32(bounty_id, "bounty_id")).call()
        keys = ("maintainer", "token", "recipient", "amount", "expires_at", "release_at", "status")
        return dict(zip(keys, values, strict=True))

    async def get_verdict(self, bounty_id: str) -> dict[str, Any]:
        values = self._registry.functions.getVerdict(_bytes32(bounty_id, "bounty_id")).call()
        keys = ("evidence_hash", "evidence_cid", "recipient", "final_score_bps", "submitted_at", "challenge_ends_at", "exists")
        return dict(zip(keys, values, strict=True))

    async def get_dispute(self, bounty_id: str) -> dict[str, Any]:
        values = self._disputes.functions.getDispute(_bytes32(bounty_id, "bounty_id")).call()
        keys = ("challenger", "evidence_cid", "opened_at", "open", "resolution")
        return dict(zip(keys, values, strict=True))

    async def get_transaction_status(self, transaction_hash: str) -> dict[str, Any]:
        status, _ = self._receipt_status(transaction_hash)
        return status

    async def get_latest_block(self) -> int:
        return self._web3.eth.block_number

    def _event_value(self, value: Any) -> Any:
        if isinstance(value, bytes):
            return self._web3.to_hex(value)
        if isinstance(value, (list, tuple)):
            return [self._event_value(item) for item in value]
        return value

    async def list_events(self, from_block: int, to_block: int | None = None) -> list[dict[str, Any]]:
        if from_block < 0 or (to_block is not None and to_block < from_block):
            raise ChainError("Invalid block range")
        sources = (
            ("bounty_escrow", self._escrow, ("BountyCreated", "VerdictRecorded", "BountyChallenged", "BountyPaid", "BountyRefunded")),
            ("verdict_registry", self._registry, ("VerdictSubmitted",)),
            ("dispute_manager", self._disputes, ("DisputeOpened", "DisputeResolved")),
        )
        events: list[dict[str, Any]] = []
        for contract_name, contract, names in sources:
            for name in names:
                logs = getattr(contract.events, name)().get_logs(from_block=from_block, to_block=to_block or "latest")
                events.extend({
                    "event": name,
                    "contract": contract_name,
                    "block_number": log["blockNumber"],
                    "transaction_hash": log["transactionHash"].hex(),
                    "log_index": log["logIndex"],
                    "args": {key: self._event_value(value) for key, value in log["args"].items()},
                } for log in logs)
        return sorted(events, key=lambda event: (event["block_number"], event["log_index"]))


def build_chain_client(settings: Settings) -> ChainClient:
    if settings.fixture_mode:
        return FixtureChainClient(settings.chain_id)
    return Web3ChainClient(settings)
