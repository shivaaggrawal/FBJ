import { network } from "hardhat";

import { requireAddress, requireBountyId, scriptArgs } from "./lib/cli.js";

/** Usage: hardhat run scripts/openDispute.ts --network amoy -- <disputeManager> <bountyId> <evidenceCid> */
async function main() {
  const [managerAddress, bountyId, evidenceCid] = scriptArgs(
    3,
    "hardhat run scripts/openDispute.ts --network amoy -- <disputeManager> <bountyId> <evidenceCid>"
  );
  const { ethers } = await network.getOrCreate();
  const disputes = await ethers.getContractAt("DisputeManager", requireAddress(managerAddress, "disputeManager"));
  const tx = await disputes.openDispute(requireBountyId(bountyId), evidenceCid);
  const receipt = await tx.wait();
  console.log(JSON.stringify({ transactionHash: receipt?.hash, bountyId }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
