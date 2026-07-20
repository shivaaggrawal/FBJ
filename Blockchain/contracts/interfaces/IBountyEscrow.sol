// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IBountyEscrow {
    enum BountyStatus {
        None,
        Open,
        VerdictSubmitted,
        Challenged,
        PaidOut,
        Refunded,
        Cancelled
    }

    struct Bounty {
        address maintainer;
        address token;
        address recipient;
        uint128 amount;
        uint64 expiresAt;
        uint64 releaseAt;
        BountyStatus status;
    }

    function getBounty(bytes32 bountyId) external view returns (Bounty memory);

    function recordVerdict(bytes32 bountyId, address recipient, uint64 releaseAt) external;

    function markDisputed(bytes32 bountyId) external;

    function resolveDisputeToRecipient(bytes32 bountyId) external;

    function resolveDisputeToMaintainer(bytes32 bountyId) external;
}

