import { network } from "hardhat";

import { requireAddress, requireBountyId, scriptArgs } from "./lib/cli.js";

/** Usage: hardhat run scripts/releaseBounty.ts --network amoy -- <escrow> <bountyId> */
async function main() {
  const [escrowAddress, bountyId] = scriptArgs(
    2,
    "hardhat run scripts/releaseBounty.ts --network amoy -- <escrow> <bountyId>"
  );
  const { ethers } = await network.getOrCreate();
  const escrow = await ethers.getContractAt("BountyEscrow", requireAddress(escrowAddress, "escrow"));
  const tx = await escrow.releaseBounty(requireBountyId(bountyId));
  const receipt = await tx.wait();
  console.log(JSON.stringify({ transactionHash: receipt?.hash, bountyId }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
