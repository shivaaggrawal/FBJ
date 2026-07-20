import { network } from "hardhat";

import { requireAddress, requireBountyId, scriptArgs } from "./lib/cli.js";

/** Usage: hardhat run scripts/resolveDispute.ts --network amoy -- <disputeManager> <bountyId> <pay|refund> */
async function main() {
  const [managerAddress, bountyId, outcome] = scriptArgs(
    3,
    "hardhat run scripts/resolveDispute.ts --network amoy -- <disputeManager> <bountyId> <pay|refund>"
  );
  const resolution = outcome === "pay" ? 1 : outcome === "refund" ? 2 : undefined;
  if (resolution === undefined) throw new Error("outcome must be either pay or refund");

  const { ethers } = await network.getOrCreate();
  const disputes = await ethers.getContractAt("DisputeManager", requireAddress(managerAddress, "disputeManager"));
  const tx = await disputes.resolveDispute(requireBountyId(bountyId), resolution);
  const receipt = await tx.wait();
  console.log(JSON.stringify({ transactionHash: receipt?.hash, bountyId, outcome }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
