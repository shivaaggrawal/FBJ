// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {IBountyEscrow} from "./interfaces/IBountyEscrow.sol";

/// @notice Custodies ERC-20 bounty funds and is the sole contract permitted to release them.
contract BountyEscrow is IBountyEscrow, AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant VERDICT_REGISTRY_ROLE = keccak256("VERDICT_REGISTRY_ROLE");
    bytes32 public constant DISPUTE_MANAGER_ROLE = keccak256("DISPUTE_MANAGER_ROLE");

    error ZeroAddress();
    error TokenMustBeContract(address token);
    error InvalidBountyId();
    error InvalidAmount();
    error InvalidExpiry();
    error DuplicateBounty(bytes32 bountyId);
    error BountyNotFound(bytes32 bountyId);
    error InvalidStatus(bytes32 bountyId, BountyStatus actual);
    error NotMaintainer(address caller);
    error BountyExpired(bytes32 bountyId);
    error BountyNotExpired(bytes32 bountyId);
    error InvalidReleaseTime();
    error PayoutNotReady(bytes32 bountyId);
    error UnsupportedTokenBehavior(address token);

    mapping(bytes32 bountyId => Bounty bounty) private bounties;

    event BountyCreated(
        bytes32 indexed bountyId,
        address indexed maintainer,
        address indexed token,
        uint256 amount,
        uint64 expiresAt
    );
    event VerdictRecorded(bytes32 indexed bountyId, address indexed recipient, uint64 releaseAt);
    event BountyChallenged(bytes32 indexed bountyId);
    event BountyPaid(bytes32 indexed bountyId, address indexed recipient, uint256 amount);
    event BountyRefunded(bytes32 indexed bountyId, address indexed maintainer, uint256 amount, BountyStatus status);
    event DefaultTokenUpdated(address indexed previousToken, address indexed newToken);

    address public defaultRewardToken;

    constructor(address admin, address initialDefaultRewardToken) {
        if (admin == address(0) || initialDefaultRewardToken == address(0)) revert ZeroAddress();
        if (initialDefaultRewardToken.code.length == 0) revert TokenMustBeContract(initialDefaultRewardToken);

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        defaultRewardToken = initialDefaultRewardToken;
    }

    function createBounty(
        bytes32 bountyId,
        address token,
        uint128 amount,
        uint64 expiresAt
    ) external whenNotPaused nonReentrant {
        if (bountyId == bytes32(0)) revert InvalidBountyId();
        if (bounties[bountyId].status != BountyStatus.None) revert DuplicateBounty(bountyId);
        if (amount == 0) revert InvalidAmount();
        if (expiresAt <= block.timestamp) revert InvalidExpiry();

        address rewardToken = token == address(0) ? defaultRewardToken : token;
        if (rewardToken == address(0)) revert ZeroAddress();
        if (rewardToken.code.length == 0) revert TokenMustBeContract(rewardToken);

        bounties[bountyId] = Bounty({
            maintainer: msg.sender,
            token: rewardToken,
            recipient: address(0),
            amount: amount,
            expiresAt: expiresAt,
            releaseAt: 0,
            status: BountyStatus.Open
        });

        uint256 balanceBefore = IERC20(rewardToken).balanceOf(address(this));
        IERC20(rewardToken).safeTransferFrom(msg.sender, address(this), amount);
        if (IERC20(rewardToken).balanceOf(address(this)) != balanceBefore + amount) {
            revert UnsupportedTokenBehavior(rewardToken);
        }
        emit BountyCreated(bountyId, msg.sender, rewardToken, amount, expiresAt);
    }

    function recordVerdict(
        bytes32 bountyId,
        address recipient,
        uint64 releaseAt
    ) external onlyRole(VERDICT_REGISTRY_ROLE) whenNotPaused {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.Open) revert InvalidStatus(bountyId, bounty.status);
        if (block.timestamp > bounty.expiresAt) revert BountyExpired(bountyId);
        if (recipient == address(0)) revert ZeroAddress();
        if (releaseAt <= block.timestamp || releaseAt > bounty.expiresAt) revert InvalidReleaseTime();

        bounty.recipient = recipient;
        bounty.releaseAt = releaseAt;
        bounty.status = BountyStatus.VerdictSubmitted;

        emit VerdictRecorded(bountyId, recipient, releaseAt);
    }

    function releaseBounty(bytes32 bountyId) external whenNotPaused nonReentrant {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.VerdictSubmitted) revert InvalidStatus(bountyId, bounty.status);
        if (block.timestamp < bounty.releaseAt) revert PayoutNotReady(bountyId);
        if (block.timestamp > bounty.expiresAt) revert BountyExpired(bountyId);

        bounty.status = BountyStatus.PaidOut;
        IERC20(bounty.token).safeTransfer(bounty.recipient, bounty.amount);
        emit BountyPaid(bountyId, bounty.recipient, bounty.amount);
    }

    function markDisputed(bytes32 bountyId) external onlyRole(DISPUTE_MANAGER_ROLE) whenNotPaused {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.VerdictSubmitted) revert InvalidStatus(bountyId, bounty.status);
        if (block.timestamp >= bounty.releaseAt) revert PayoutNotReady(bountyId);

        bounty.status = BountyStatus.Challenged;
        emit BountyChallenged(bountyId);
    }

    function resolveDisputeToRecipient(
        bytes32 bountyId
    ) external onlyRole(DISPUTE_MANAGER_ROLE) whenNotPaused nonReentrant {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.Challenged) revert InvalidStatus(bountyId, bounty.status);

        bounty.status = BountyStatus.PaidOut;
        IERC20(bounty.token).safeTransfer(bounty.recipient, bounty.amount);
        emit BountyPaid(bountyId, bounty.recipient, bounty.amount);
    }

    function resolveDisputeToMaintainer(
        bytes32 bountyId
    ) external onlyRole(DISPUTE_MANAGER_ROLE) whenNotPaused nonReentrant {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.Challenged) revert InvalidStatus(bountyId, bounty.status);

        bounty.status = BountyStatus.Refunded;
        IERC20(bounty.token).safeTransfer(bounty.maintainer, bounty.amount);
        emit BountyRefunded(bountyId, bounty.maintainer, bounty.amount, BountyStatus.Refunded);
    }

    function cancelOpenBounty(bytes32 bountyId) external whenNotPaused nonReentrant {
        Bounty storage bounty = _bounty(bountyId);
        if (msg.sender != bounty.maintainer) revert NotMaintainer(msg.sender);
        if (bounty.status != BountyStatus.Open) revert InvalidStatus(bountyId, bounty.status);

        bounty.status = BountyStatus.Cancelled;
        IERC20(bounty.token).safeTransfer(bounty.maintainer, bounty.amount);
        emit BountyRefunded(bountyId, bounty.maintainer, bounty.amount, BountyStatus.Cancelled);
    }

    function refundExpiredBounty(bytes32 bountyId) external whenNotPaused nonReentrant {
        Bounty storage bounty = _bounty(bountyId);
        if (bounty.status != BountyStatus.Open) revert InvalidStatus(bountyId, bounty.status);
        if (block.timestamp <= bounty.expiresAt) revert BountyNotExpired(bountyId);

        bounty.status = BountyStatus.Refunded;
        IERC20(bounty.token).safeTransfer(bounty.maintainer, bounty.amount);
        emit BountyRefunded(bountyId, bounty.maintainer, bounty.amount, BountyStatus.Refunded);
    }

    function setDefaultRewardToken(address newToken) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (newToken == address(0)) revert ZeroAddress();
        if (newToken.code.length == 0) revert TokenMustBeContract(newToken);
        address previousToken = defaultRewardToken;
        defaultRewardToken = newToken;
        emit DefaultTokenUpdated(previousToken, newToken);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    function getBounty(bytes32 bountyId) external view returns (Bounty memory) {
        return _bounty(bountyId);
    }

    function _bounty(bytes32 bountyId) private view returns (Bounty storage bounty) {
        bounty = bounties[bountyId];
        if (bounty.status == BountyStatus.None) revert BountyNotFound(bountyId);
    }
}
