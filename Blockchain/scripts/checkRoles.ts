import { network } from "hardhat";

function requiredAddress(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function requireContract(ethers: Awaited<ReturnType<typeof network.getOrCreate>>["ethers"], name: string, address: string) {
  if (!ethers.isAddress(address)) throw new Error(`${name} must be a valid address`);
  if ((await ethers.provider.getCode(address)) === "0x") throw new Error(`${name} has no deployed contract code`);
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const escrowAddress = requiredAddress("BOUNTY_ESCROW_ADDRESS");
  const verdictRegistryAddress = requiredAddress("VERDICT_REGISTRY_ADDRESS");
  const disputeManagerAddress = requiredAddress("DISPUTE_MANAGER_ADDRESS");
  const relayer = requiredAddress("RELAYER_ADDRESS");
  const disputeResolver = requiredAddress("DISPUTE_RESOLVER_ADDRESS");

  for (const [name, address] of Object.entries({
    BOUNTY_ESCROW_ADDRESS: escrowAddress,
    VERDICT_REGISTRY_ADDRESS: verdictRegistryAddress,
    DISPUTE_MANAGER_ADDRESS: disputeManagerAddress
  })) {
    await requireContract(ethers, name, address);
  }
  if (!ethers.isAddress(relayer)) throw new Error("RELAYER_ADDRESS must be a valid address");
  if (!ethers.isAddress(disputeResolver)) throw new Error("DISPUTE_RESOLVER_ADDRESS must be a valid address");

  const escrow = await ethers.getContractAt("BountyEscrow", escrowAddress);
  const verdictRegistry = await ethers.getContractAt("VerdictRegistry", verdictRegistryAddress);
  const disputeManager = await ethers.getContractAt("DisputeManager", disputeManagerAddress);
  const defaultRewardToken = await escrow.defaultRewardToken();

  const checks = {
    registryUsesEscrow: ethers.getAddress(await verdictRegistry.escrow()) === ethers.getAddress(escrowAddress),
    disputeManagerUsesEscrow: ethers.getAddress(await disputeManager.escrow()) === ethers.getAddress(escrowAddress),
    disputeManagerUsesRegistry: ethers.getAddress(await disputeManager.verdictRegistry()) === ethers.getAddress(verdictRegistryAddress),
    registryCanRecordVerdicts: await escrow.hasRole(await escrow.VERDICT_REGISTRY_ROLE(), verdictRegistryAddress),
    disputeManagerCanResolveEscrow: await escrow.hasRole(await escrow.DISPUTE_MANAGER_ROLE(), disputeManagerAddress),
    relayerCanSubmitVerdicts: await verdictRegistry.hasRole(await verdictRegistry.RELAYER_ROLE(), relayer),
    resolverCanResolveDisputes: await disputeManager.hasRole(await disputeManager.DISPUTE_ROLE(), disputeResolver)
  };

  const deployedNetwork = await ethers.provider.getNetwork();
  console.log(JSON.stringify({
    chainId: deployedNetwork.chainId.toString(),
    bountyEscrow: escrowAddress,
    verdictRegistry: verdictRegistryAddress,
    disputeManager: disputeManagerAddress,
    defaultRewardToken,
    relayer,
    disputeResolver,
    checks,
    ready: Object.values(checks).every(Boolean)
  }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
