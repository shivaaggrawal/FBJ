// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

import {IBountyEscrow} from "./interfaces/IBountyEscrow.sol";
import {IVerdictRegistry} from "./interfaces/IVerdictRegistry.sol";
import {IpfsCid} from "./libraries/IpfsCid.sol";

/// @notice Anchors a content-addressed AI evidence bundle and starts its challenge window.
contract VerdictRegistry is IVerdictRegistry, AccessControl, Pausable {
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    uint16 public constant MAX_SCORE_BPS = 10_000;

    error ZeroAddress();
    error EscrowMustBeContract(address escrowAddress);
    error InvalidEvidenceHash();
    error InvalidEvidenceCid();
    error InvalidScore(uint16 score);
    error ScoreBelowThreshold(uint16 score, uint16 threshold);
    error VerdictAlreadyExists(bytes32 bountyId);
    error InvalidChallengePeriod();
    error ChallengeWindowExceedsBounty(bytes32 bountyId);

    IBountyEscrow public immutable escrow;
    uint16 public minimumPassingScoreBps;
    uint64 public challengePeriod;

    mapping(bytes32 bountyId => Verdict verdict) private verdicts;

    event VerdictSubmitted(
        bytes32 indexed bountyId,
        bytes32 indexed evidenceHash,
        address indexed recipient,
        string evidenceCid,
        uint16 finalScoreBps,
        uint64 challengeEndsAt
    );
    event MinimumPassingScoreUpdated(uint16 previousScore, uint16 newScore);
    event ChallengePeriodUpdated(uint64 previousPeriod, uint64 newPeriod);

    constructor(
        address admin,
        address escrowAddress,
        address initialRelayer,
        uint16 initialMinimumPassingScoreBps,
        uint64 initialChallengePeriod
    ) {
        if (admin == address(0) || escrowAddress == address(0) || initialRelayer == address(0)) revert ZeroAddress();
        if (escrowAddress.code.length == 0) revert EscrowMustBeContract(escrowAddress);
        if (initialMinimumPassingScoreBps > MAX_SCORE_BPS) revert InvalidScore(initialMinimumPassingScoreBps);
        if (initialChallengePeriod == 0) revert InvalidChallengePeriod();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RELAYER_ROLE, initialRelayer);
        escrow = IBountyEscrow(escrowAddress);
        minimumPassingScoreBps = initialMinimumPassingScoreBps;
        challengePeriod = initialChallengePeriod;
    }

    function submitVerdict(
        bytes32 bountyId,
        bytes32 evidenceHash,
        string calldata evidenceCid,
        address recipient,
        uint16 finalScoreBps
    ) external onlyRole(RELAYER_ROLE) whenNotPaused {
        if (evidenceHash == bytes32(0)) revert InvalidEvidenceHash();
        if (!_isValidCid(evidenceCid)) revert InvalidEvidenceCid();
        if (recipient == address(0)) revert ZeroAddress();
        if (finalScoreBps > MAX_SCORE_BPS) revert InvalidScore(finalScoreBps);
        if (finalScoreBps < minimumPassingScoreBps) {
            revert ScoreBelowThreshold(finalScoreBps, minimumPassingScoreBps);
        }
        if (verdicts[bountyId].exists) revert VerdictAlreadyExists(bountyId);

        IBountyEscrow.Bounty memory bounty = escrow.getBounty(bountyId);
        uint256 releaseAt = block.timestamp + challengePeriod;
        if (releaseAt > bounty.expiresAt) revert ChallengeWindowExceedsBounty(bountyId);

        uint64 challengeEndsAt = uint64(releaseAt);
        verdicts[bountyId] = Verdict({
            evidenceHash: evidenceHash,
            evidenceCid: evidenceCid,
            recipient: recipient,
            finalScoreBps: finalScoreBps,
            submittedAt: uint64(block.timestamp),
            challengeEndsAt: challengeEndsAt,
            exists: true
        });

        escrow.recordVerdict(bountyId, recipient, challengeEndsAt);
        emit VerdictSubmitted(bountyId, evidenceHash, recipient, evidenceCid, finalScoreBps, challengeEndsAt);
    }

    function setMinimumPassingScoreBps(uint16 newScore) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newScore > MAX_SCORE_BPS) revert InvalidScore(newScore);
        uint16 previousScore = minimumPassingScoreBps;
        minimumPassingScoreBps = newScore;
        emit MinimumPassingScoreUpdated(previousScore, newScore);
    }

    function setChallengePeriod(uint64 newPeriod) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newPeriod == 0) revert InvalidChallengePeriod();
        uint64 previousPeriod = challengePeriod;
        challengePeriod = newPeriod;
        emit ChallengePeriodUpdated(previousPeriod, newPeriod);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function getVerdict(bytes32 bountyId) external view returns (Verdict memory) {
        return verdicts[bountyId];
    }

    function _isValidCid(string calldata cid) private pure returns (bool) {
        return IpfsCid.isValid(cid);
    }
}
