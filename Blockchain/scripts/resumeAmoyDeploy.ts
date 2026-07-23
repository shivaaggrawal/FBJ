import { network } from "hardhat";

const DAY = 24 * 60 * 60;
const gasUsage: Array<{ label: string; gasUsed: string }> = [];

function requiredAddress(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function requireContract(ethers: Awaited<ReturnType<typeof network.getOrCreate>>["ethers"], name: string, address: string) {
  if (!ethers.isAddress(address)) throw new Error(`${name} must be a valid address`);
  if ((await ethers.provider.getCode(address)) === "0x") throw new Error(`${name} has no deployed contract code`);
}

async function waitForTransaction(label: string, transaction: { wait: () => Promise<{ gasUsed: bigint } | null> }) {
  const receipt = await transaction.wait();
  if (receipt === null) throw new Error(`${label} transaction was not mined`);
  gasUsage.push({ label, gasUsed: receipt.gasUsed.toString() });
  console.log(`${label}: ${receipt.gasUsed.toString()} gas used`);
}

async function reportDeploymentGas(
  label: string,
  contract: { deploymentTransaction: () => { wait: () => Promise<{ gasUsed: bigint } | null> } | null }
) {
  const transaction = contract.deploymentTransaction();
  if (transaction === null) throw new Error(`${label} deployment transaction is unavailable`);
  await waitForTransaction(`${label} deployment`, transaction);
}

async function ensureRole(
  label: string,
  contract: any,
  role: string,
  account: string
) {
  if (await contract.hasRole(role, account)) {
    console.log(`${label}: already granted`);
    return;
  }
  await waitForTransaction(label, await contract.grantRole(role, account));
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const [deployer] = await ethers.getSigners();
  const admin = deployer.address;
  const escrowAddress = requiredAddress("BOUNTY_ESCROW_ADDRESS");
  await requireContract(ethers, "BOUNTY_ESCROW_ADDRESS", escrowAddress);

  const relayer = process.env.RELAYER_ADDRESS ?? admin;
  const disputeResolver = process.env.DISPUTE_RESOLVER_ADDRESS ?? admin;
  if (!ethers.isAddress(relayer)) throw new Error("RELAYER_ADDRESS must be a valid address");
  if (!ethers.isAddress(disputeResolver)) throw new Error("DISPUTE_RESOLVER_ADDRESS must be a valid address");

  const escrow = await ethers.getContractAt("BountyEscrow", escrowAddress);
  const defaultRewardToken = await escrow.defaultRewardToken();
  const configuredRewardToken = process.env.DEFAULT_REWARD_TOKEN;
  if (configuredRewardToken && ethers.getAddress(configuredRewardToken) !== ethers.getAddress(defaultRewardToken)) {
    throw new Error("DEFAULT_REWARD_TOKEN does not match BountyEscrow.defaultRewardToken()");
  }

  let verdictRegistry;
  const existingRegistryAddress = process.env.VERDICT_REGISTRY_ADDRESS;
  if (existingRegistryAddress) {
    await requireContract(ethers, "VERDICT_REGISTRY_ADDRESS", existingRegistryAddress);
    verdictRegistry = await ethers.getContractAt("VerdictRegistry", existingRegistryAddress);
    if (ethers.getAddress(await verdictRegistry.escrow()) !== ethers.getAddress(escrowAddress)) {
      throw new Error("VERDICT_REGISTRY_ADDRESS is connected to a different escrow contract");
    }
    console.log(`Reusing VerdictRegistry at ${await verdictRegistry.getAddress()}`);
  } else {
    const VerdictRegistry = await ethers.getContractFactory("VerdictRegistry");
    verdictRegistry = await VerdictRegistry.deploy(admin, escrowAddress, relayer, 7_000, 3 * DAY);
    await verdictRegistry.waitForDeployment();
    console.log(`VerdictRegistry deployed at ${await verdictRegistry.getAddress()}`);
    await reportDeploymentGas("VerdictRegistry", verdictRegistry);
  }

  await ensureRole(
    "Grant relayer role",
    verdictRegistry,
    await verdictRegistry.RELAYER_ROLE(),
    relayer
  );
  await ensureRole(
    "Grant VerdictRegistry escrow role",
    escrow,
    await escrow.VERDICT_REGISTRY_ROLE(),
    await verdictRegistry.getAddress()
  );

  let disputeManager;
  const existingDisputeManagerAddress = process.env.DISPUTE_MANAGER_ADDRESS;
  if (existingDisputeManagerAddress) {
    await requireContract(ethers, "DISPUTE_MANAGER_ADDRESS", existingDisputeManagerAddress);
    disputeManager = await ethers.getContractAt("DisputeManager", existingDisputeManagerAddress);
    if (ethers.getAddress(await disputeManager.escrow()) !== ethers.getAddress(escrowAddress)) {
      throw new Error("DISPUTE_MANAGER_ADDRESS is connected to a different escrow contract");
    }
    if (ethers.getAddress(await disputeManager.verdictRegistry()) !== ethers.getAddress(await verdictRegistry.getAddress())) {
      throw new Error("DISPUTE_MANAGER_ADDRESS is connected to a different VerdictRegistry contract");
    }
    console.log(`Reusing DisputeManager at ${await disputeManager.getAddress()}`);
  } else {
    const DisputeManager = await ethers.getContractFactory("DisputeManager");
    disputeManager = await DisputeManager.deploy(admin, escrowAddress, await verdictRegistry.getAddress(), disputeResolver);
    await disputeManager.waitForDeployment();
    console.log(`DisputeManager deployed at ${await disputeManager.getAddress()}`);
    await reportDeploymentGas("DisputeManager", disputeManager);
  }

  await ensureRole(
    "Grant dispute resolver role",
    disputeManager,
    await disputeManager.DISPUTE_ROLE(),
    disputeResolver
  );
  await ensureRole(
    "Grant DisputeManager escrow role",
    escrow,
    await escrow.DISPUTE_MANAGER_ROLE(),
    await disputeManager.getAddress()
  );

  const deployedNetwork = await ethers.provider.getNetwork();
  console.log(JSON.stringify({
    chainId: deployedNetwork.chainId.toString(),
    deployer: admin,
    bountyEscrow: escrowAddress,
    verdictRegistry: await verdictRegistry.getAddress(),
    disputeManager: await disputeManager.getAddress(),
    defaultRewardToken,
    relayer,
    disputeResolver,
    gasUsage,
    totalGasUsed: gasUsage.reduce((total, transaction) => total + BigInt(transaction.gasUsed), 0n).toString(),
    backendEnv: {
      CHAIN_ID: deployedNetwork.chainId.toString(),
      BOUNTY_ESCROW_ADDRESS: escrowAddress,
      VERDICT_REGISTRY_ADDRESS: await verdictRegistry.getAddress(),
      DISPUTE_MANAGER_ADDRESS: await disputeManager.getAddress(),
      REWARD_TOKEN_ADDRESS: defaultRewardToken
    }
  }, null, 2));
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
