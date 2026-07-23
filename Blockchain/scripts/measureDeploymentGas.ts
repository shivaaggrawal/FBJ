import { network } from "hardhat";

const DAY = 24 * 60 * 60;

async function receiptGas(label: string, transaction: { wait: () => Promise<{ gasUsed: bigint } | null> }) {
  const receipt = await transaction.wait();
  if (receipt === null) throw new Error(`${label} transaction was not mined`);
  return { label, gasUsed: receipt.gasUsed };
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const [admin, relayer, resolver] = await ethers.getSigners();
  const Token = await ethers.getContractFactory("MockUSDC");
  const token = await Token.deploy();
  await token.waitForDeployment();

  const Escrow = await ethers.getContractFactory("BountyEscrow");
  const escrow = await Escrow.deploy(admin.address, await token.getAddress());
  await escrow.waitForDeployment();

  const Registry = await ethers.getContractFactory("VerdictRegistry");
  const registry = await Registry.deploy(admin.address, await escrow.getAddress(), relayer.address, 7_000, 3 * DAY);
  await registry.waitForDeployment();

  const Disputes = await ethers.getContractFactory("DisputeManager");
  const disputes = await Disputes.deploy(admin.address, await escrow.getAddress(), await registry.getAddress(), resolver.address);
  await disputes.waitForDeployment();

  const gas = [
    await receiptGas("BountyEscrow deployment", escrow.deploymentTransaction()!),
    await receiptGas("VerdictRegistry deployment", registry.deploymentTransaction()!),
    await receiptGas("DisputeManager deployment", disputes.deploymentTransaction()!),
    await receiptGas("Grant VerdictRegistry role", await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), await registry.getAddress())),
    await receiptGas("Grant DisputeManager role", await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), await disputes.getAddress()))
  ];

  console.log(JSON.stringify({
    gas: gas.map((transaction) => ({ label: transaction.label, gasUsed: transaction.gasUsed.toString() })),
    totalGasUsed: gas.reduce((total, transaction) => total + transaction.gasUsed, 0n).toString()
  }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
