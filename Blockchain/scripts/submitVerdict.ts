import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { network } from "hardhat";

import { requireAddress, requireBountyId, scriptArgs } from "./lib/cli.js";

/**
 * Sends a verdict after the backend has uploaded the exact JSON bytes to IPFS.
 * Usage: hardhat run scripts/submitVerdict.ts --network amoy -- <registry> <bountyId> <cid> <recipient> <scoreBps> <evidence.json>
 */
async function main() {
  const [registryAddress, bountyId, cid, recipient, scoreInput, evidencePath] = scriptArgs(
    6,
    "hardhat run scripts/submitVerdict.ts --network amoy -- <registry> <bountyId> <cid> <recipient> <scoreBps> <evidence.json>"
  );

  const evidenceBytes = await readFile(evidencePath);
  const sha256 = createHash("sha256").update(evidenceBytes).digest("hex");
  const { ethers } = await network.getOrCreate();
  const registry = await ethers.getContractAt("VerdictRegistry", requireAddress(registryAddress, "registry"));
  const evidenceHash = ethers.keccak256(evidenceBytes);

  const tx = await registry.submitVerdict(
    requireBountyId(bountyId),
    evidenceHash,
    cid,
    requireAddress(recipient, "recipient"),
    Number(requirePositiveScore(scoreInput))
  );
  const receipt = await tx.wait();
  console.log(JSON.stringify({ transactionHash: receipt?.hash, evidenceHash, sha256 }, null, 2));
}

function requirePositiveScore(value: string): bigint {
  if (!/^[0-9]{1,5}$/.test(value) || BigInt(value) > 10_000n) {
    throw new Error("scoreBps must be an integer from 0 to 10000");
  }
  return BigInt(value);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
