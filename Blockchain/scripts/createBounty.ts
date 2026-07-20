import { Contract } from "ethers";
import { network } from "hardhat";

import { requireAddress, requireBountyId, requirePositiveInteger, scriptArgs } from "./lib/cli.js";

const ERC20_APPROVE_ABI = ["function approve(address spender, uint256 value) external returns (bool)"];

/**
 * Approves the escrow and creates a bounty from the configured deployer wallet.
 * Usage: hardhat run scripts/createBounty.ts --network amoy -- <escrow> <token|0x0> <bountyId> <amount> <expiresAtUnix>
 */
async function main() {
  const [escrowAddress, requestedToken, bountyId, amountInput, expiryInput] = scriptArgs(
    5,
    "hardhat run scripts/createBounty.ts --network amoy -- <escrow> <token|0x0> <bountyId> <amount> <expiresAtUnix>"
  );
  const { ethers } = await network.getOrCreate();
  const [maintainer] = await ethers.getSigners();
  const escrow = await ethers.getContractAt("BountyEscrow", requireAddress(escrowAddress, "escrow"));
  const token = requestedToken === ethers.ZeroAddress
    ? await escrow.defaultRewardToken()
    : requireAddress(requestedToken, "token");
  const bountyAmount = requirePositiveInteger(amountInput, "amount");
  const expiresAt = requirePositiveInteger(expiryInput, "expiresAtUnix");
  const latestBlock = await ethers.provider.getBlock("latest");
  if (expiresAt <= BigInt(latestBlock!.timestamp)) throw new Error("expiresAtUnix must be in the future");

  const rewardToken = new Contract(token, ERC20_APPROVE_ABI, maintainer);
  const approval = await rewardToken.approve(await escrow.getAddress(), bountyAmount);
  await approval.wait();
  const createTx = await escrow.createBounty(requireBountyId(bountyId), requestedToken, bountyAmount, expiresAt);
  const receipt = await createTx.wait();

  console.log(JSON.stringify({ approvalHash: approval.hash, transactionHash: receipt?.hash, bountyId, token }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
