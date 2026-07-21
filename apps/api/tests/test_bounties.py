import asyncio

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.bounties import BountyRegistrationError, registration_message, verify_on_chain_bounty
from app.config import Settings
from app.main import app, get_chain, get_settings, get_store
from app.schemas import BountyRegistrationRequest
from app.store import MemoryStore


class ConfirmedBountyChain:
    async def verify_bounty_creation(self, bounty_id: str, transaction_hash: str) -> dict:
        return {
            "transaction_hash": transaction_hash,
            "block_number": 123,
            "network": "80002",
            "status": "confirmed",
        }

    async def get_bounty(self, bounty_id: str) -> dict:
        return {
            "maintainer": ACCOUNT.address,
            "token": "0x" + "12" * 20,
            "amount": 1_000_000,
            "expires_at": 1_900_000_000,
            "status": 1,
        }


ACCOUNT = Account.create()
SETTINGS = Settings(
    fixture_mode=False,
    chain_id=80002,
    bounty_escrow_address="0x" + "ef" * 20,
)


def signed_bounty() -> BountyRegistrationRequest:
    bounty = BountyRegistrationRequest(
        contract_bounty_id="0x" + "ab" * 32,
        repository="owner/repository",
        issue_url="https://github.com/owner/repository/issues/1",
        criteria="Add the feature with tests.",
        reward_token="0x" + "12" * 20,
        reward_amount="1000000",
        maintainer_wallet=ACCOUNT.address,
        expires_at=1_900_000_000,
        challenge_seconds=3600,
        creation_tx_hash="0x" + "cd" * 32,
    )
    signature = ACCOUNT.sign_message(encode_defunct(text=registration_message(bounty, SETTINGS))).signature.hex()
    return bounty.model_copy(update={"registration_signature": signature})


def test_verified_bounty_registration_matches_the_confirmed_escrow_state():
    verified = asyncio.run(verify_on_chain_bounty(signed_bounty(), ConfirmedBountyChain(), SETTINGS))
    assert verified == {
        "reward_token": "0x" + "12" * 20,
        "creation_tx_hash": "0x" + "cd" * 32,
        "creation_block_number": 123,
        "chain_id": 80002,
    }


def test_bounty_registration_rejects_a_signature_from_anyone_other_than_the_maintainer():
    bounty = signed_bounty()
    attacker = Account.create()
    forged = attacker.sign_message(encode_defunct(text=registration_message(bounty, SETTINGS))).signature.hex()
    with pytest.raises(BountyRegistrationError, match="on-chain maintainer"):
        asyncio.run(verify_on_chain_bounty(bounty.model_copy(update={"registration_signature": forged}), ConfirmedBountyChain(), SETTINGS))


def test_production_registration_api_persists_only_a_verified_bounty():
    store = MemoryStore()
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.update({
        get_store: lambda: store,
        get_chain: lambda: ConfirmedBountyChain(),
        get_settings: lambda: SETTINGS,
    })
    try:
        response = TestClient(app).post("/api/bounties", json=signed_bounty().model_dump())
    finally:
        app.dependency_overrides = previous_overrides

    assert response.status_code == 201
    payload = response.json()
    assert payload["chain_id"] == 80002
    assert payload["creation_tx_hash"] == "0x" + "cd" * 32
    assert asyncio.run(store.get_bounty("0x" + "ab" * 32))["creation_block_number"] == 123
