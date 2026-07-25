"""Validates an on-chain bounty before it is registered for PR review."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .chain import ChainClient, ChainError
from .config import Settings
from .schemas import BountyRegistrationRequest, ClaimBountyRequest

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
OPEN_BOUNTY_STATUS = 1


class BountyRegistrationError(RuntimeError):
    pass


class BountyClaimError(RuntimeError):
    pass


def registration_message(bounty: BountyRegistrationRequest, settings: Settings) -> str:
    """Return the exact message that the on-chain maintainer must sign."""
    if bounty.creation_tx_hash is None:
        raise BountyRegistrationError("creation_tx_hash is required for on-chain bounty registration")
    if not settings.bounty_escrow_address:
        raise BountyRegistrationError("BOUNTY_ESCROW_ADDRESS is not configured")
    payload = {
        "chainId": settings.chain_id,
        "creationTxHash": bounty.creation_tx_hash.lower(),
        "criteria": bounty.criteria,
        "escrow": settings.bounty_escrow_address.lower(),
        "expiresAt": bounty.expires_at,
        "issueUrl": bounty.issue_url,
        "maintainer": bounty.maintainer_wallet.lower(),
        "bountyId": bounty.contract_bounty_id.lower(),
        "recipient": (bounty.recipient_wallet or "").lower(),
        "repository": bounty.repository,
        "requestedRewardToken": bounty.reward_token.lower(),
        "rewardAmount": bounty.reward_amount,
    }
    return "Fair Bounty Judge Bounty Registration\n" + json.dumps(payload, sort_keys=True, separators=(",", ":"))


def verify_registration_signature(bounty: BountyRegistrationRequest, settings: Settings) -> None:
    if bounty.registration_signature is None:
        raise BountyRegistrationError("registration_signature is required for on-chain bounty registration")
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        signer = Account.recover_message(
            encode_defunct(text=registration_message(bounty, settings)),
            signature=bounty.registration_signature,
        )
    except Exception as exc:
        raise BountyRegistrationError("registration_signature is invalid") from exc
    if signer.lower() != bounty.maintainer_wallet.lower():
        raise BountyRegistrationError("registration_signature was not made by the on-chain maintainer")


def claim_message(contract_bounty_id: str, claim: ClaimBountyRequest, settings: Settings) -> str:
    """Return the wallet-signed declaration that binds a contributor to a bounty."""
    payload = {
        "bountyId": contract_bounty_id.lower(),
        "chainId": settings.chain_id,
        "claimCode": claim.claim_code,
        "contributorGitHubLogin": claim.contributor_github_login,
        "contributorWallet": claim.contributor_wallet.lower(),
    }
    return "Fair Bounty Judge Bounty Claim\n" + json.dumps(payload, sort_keys=True, separators=(",", ":"))


def verify_claim_signature(contract_bounty_id: str, claim: ClaimBountyRequest, settings: Settings) -> None:
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        signer = Account.recover_message(
            encode_defunct(text=claim_message(contract_bounty_id, claim, settings)),
            signature=claim.claim_signature,
        )
    except Exception as exc:
        raise BountyClaimError("claim_signature is invalid") from exc
    if signer.lower() != claim.contributor_wallet.lower():
        raise BountyClaimError("claim_signature was not made by the contributor wallet")


def claim_values(claim: ClaimBountyRequest, settings: Settings) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "recipient_wallet": claim.contributor_wallet.lower(),
        "contributor_wallet": claim.contributor_wallet.lower(),
        "contributor_github_login": claim.contributor_github_login,
        "claim_code": claim.claim_code,
        "claimed_at": now,
        "claim_expires_at": int(now.timestamp()) + settings.claim_seconds,
    }


async def verify_on_chain_bounty(
    bounty: BountyRegistrationRequest, chain: ChainClient, settings: Settings
) -> dict[str, Any]:
    if bounty.creation_tx_hash is None:
        raise BountyRegistrationError("creation_tx_hash is required for on-chain bounty registration")
    verify_registration_signature(bounty, settings)
    try:
        transaction = await chain.verify_bounty_creation(bounty.contract_bounty_id, bounty.creation_tx_hash)
        on_chain = await chain.get_bounty(bounty.contract_bounty_id)
    except ChainError as exc:
        raise BountyRegistrationError(str(exc)) from exc

    expected_token = bounty.reward_token.lower()
    actual_token = str(on_chain["token"]).lower()
    mismatches = []
    if str(on_chain["maintainer"]).lower() != bounty.maintainer_wallet.lower():
        mismatches.append("maintainer_wallet")
    if expected_token != ZERO_ADDRESS and actual_token != expected_token:
        mismatches.append("reward_token")
    if int(on_chain["amount"]) != int(bounty.reward_amount):
        mismatches.append("reward_amount")
    if int(on_chain["expires_at"]) != bounty.expires_at:
        mismatches.append("expires_at")
    if int(on_chain["status"]) != OPEN_BOUNTY_STATUS:
        mismatches.append("status (bounty must be open)")
    if mismatches:
        raise BountyRegistrationError("On-chain bounty does not match: " + ", ".join(mismatches))

    return {
        "reward_token": actual_token,
        "creation_tx_hash": transaction["transaction_hash"],
        "creation_block_number": transaction["block_number"],
        "chain_id": settings.chain_id,
    }
