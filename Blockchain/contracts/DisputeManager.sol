// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

import {IBountyEscrow} from "./interfaces/IBountyEscrow.sol";
import {IVerdictRegistry} from "./interfaces/IVerdictRegistry.sol";
import {IpfsCid} from "./libraries/IpfsCid.sol";

/// @notice Captures a dispute trail and gives a designated adjudicator authority to resolve it.
contract DisputeManager is AccessControl, Pausable, ReentrancyGuard {
    bytes32 public constant DISPUTE_ROLE = keccak256("DISPUTE_ROLE");

    enum Resolution {
        None,
        PayRecipient,
        RefundMaintainer
    }

    struct Dispute {
        address challenger;
        string evidenceCid;
        uint64 openedAt;
        bool open;
        Resolution resolution;
    }

    error ZeroAddress();
    error DependencyMustBeContract(address dependency);
    error InvalidDisputeEvidence();
    error InvalidResolution(Resolution resolution);
    error UnauthorizedChallenger(address caller);
    error DisputeAlreadyExists(bytes32 bountyId);
    error DisputeNotOpen(bytes32 bountyId);

    IBountyEscrow public immutable escrow;
    IVerdictRegistry public immutable verdictRegistry;

    mapping(bytes32 bountyId => Dispute dispute) private disputes;

    event DisputeOpened(bytes32 indexed bountyId, address indexed challenger, string evidenceCid);
    event DisputeResolved(bytes32 indexed bountyId, Resolution resolution, address indexed resolver);

    constructor(address admin, address escrowAddress, address verdictRegistryAddress) {
        if (admin == address(0) || escrowAddress == address(0) || verdictRegistryAddress == address(0)) {
            revert ZeroAddress();
        }
        if (escrowAddress.code.length == 0) revert DependencyMustBeContract(escrowAddress);
        if (verdictRegistryAddress.code.length == 0) revert DependencyMustBeContract(verdictRegistryAddress);

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        escrow = IBountyEscrow(escrowAddress);
        verdictRegistry = IVerdictRegistry(verdictRegistryAddress);
    }

    function openDispute(bytes32 bountyId, string calldata evidenceCid) external whenNotPaused nonReentrant {
        if (!IpfsCid.isValid(evidenceCid)) revert InvalidDisputeEvidence();
        if (disputes[bountyId].openedAt != 0) revert DisputeAlreadyExists(bountyId);

        IBountyEscrow.Bounty memory bounty = escrow.getBounty(bountyId);
        IVerdictRegistry.Verdict memory verdict = verdictRegistry.getVerdict(bountyId);
        if (msg.sender != bounty.maintainer && msg.sender != verdict.recipient) {
            revert UnauthorizedChallenger(msg.sender);
        }

        disputes[bountyId] = Dispute({
            challenger: msg.sender,
            evidenceCid: evidenceCid,
            openedAt: uint64(block.timestamp),
            open: true,
            resolution: Resolution.None
        });

        escrow.markDisputed(bountyId);
        emit DisputeOpened(bountyId, msg.sender, evidenceCid);
    }

    function resolveDispute(
        bytes32 bountyId,
        Resolution resolution
    ) external onlyRole(DISPUTE_ROLE) whenNotPaused nonReentrant {
        Dispute storage dispute = disputes[bountyId];
        if (!dispute.open) revert DisputeNotOpen(bountyId);
        if (resolution != Resolution.PayRecipient && resolution != Resolution.RefundMaintainer) {
            revert InvalidResolution(resolution);
        }

        dispute.open = false;
        dispute.resolution = resolution;

        if (resolution == Resolution.PayRecipient) {
            escrow.resolveDisputeToRecipient(bountyId);
        } else {
            escrow.resolveDisputeToMaintainer(bountyId);
        }

        emit DisputeResolved(bountyId, resolution, msg.sender);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function getDispute(bytes32 bountyId) external view returns (Dispute memory) {
        return disputes[bountyId];
    }
}
