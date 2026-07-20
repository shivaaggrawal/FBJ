// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

interface IVerdictRegistry {
    struct Verdict {
        bytes32 evidenceHash;
        string evidenceCid;
        address recipient;
        uint16 finalScoreBps;
        uint64 submittedAt;
        uint64 challengeEndsAt;
        bool exists;
    }

    function getVerdict(bytes32 bountyId) external view returns (Verdict memory);
}

