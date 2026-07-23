import { network } from "hardhat";

const DAY = 24 * 60 * 60;
const gasUsage: Array<{ label: string; gasUsed: string }> = [];

async function waitForTransaction(label: string, transaction: { wait: () => Promise<{ gasUsed: bigint } | null> }) {
  const receipt = await transaction.wait();
  if (receipt === null) {
    throw new Error(`${label} transaction was not mined`);
  }
  gasUsage.push({ label, gasUsed: receipt.gasUsed.toString() });
  console.log(`${label}: ${receipt.gasUsed.toString()} gas used`);
}

async function reportDeploymentGas(
  label: string,
  contract: { deploymentTransaction: () => { wait: () => Promise<{ gasUsed: bigint } | null> } | null }
) {
  const transaction = contract.deploymentTransaction();
  if (transaction === null) {
    throw new Error(`${label} deployment transaction is unavailable`);
  }
  await waitForTransaction(`${label} deployment`, transaction);
}

function resolveRewardToken() {
  const configuredRewardToken = process.env.DEFAULT_REWARD_TOKEN;
  if (!configuredRewardToken) {
    throw new Error(
      "DEFAULT_REWARD_TOKEN is required for deploy:amoy. Deploy or select a demo ERC-20 first with deploy:mock-usdc:amoy."
    );
  }
  return configuredRewardToken;
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const [deployer] = await ethers.getSigners();
  const rewardToken = resolveRewardToken();

  const admin = deployer.address;
  const relayer = process.env.RELAYER_ADDRESS ?? admin;
  const disputeResolver = process.env.DISPUTE_RESOLVER_ADDRESS ?? admin;

  const Escrow = await ethers.getContractFactory("BountyEscrow");
  console.log("Deploying BountyEscrow...");
  const escrow = await Escrow.deploy(admin, rewardToken);
  await escrow.waitForDeployment();
  console.log(`BountyEscrow deployed at ${await escrow.getAddress()}`);
  await reportDeploymentGas("BountyEscrow", escrow);

  const VerdictRegistry = await ethers.getContractFactory("VerdictRegistry");
  console.log("Deploying VerdictRegistry...");
  const verdictRegistry = await VerdictRegistry.deploy(
    admin,
    await escrow.getAddress(),
    relayer,
    7_000,
    3 * DAY
  );
  await verdictRegistry.waitForDeployment();
  console.log(`VerdictRegistry deployed at ${await verdictRegistry.getAddress()}`);
  await reportDeploymentGas("VerdictRegistry", verdictRegistry);

  const DisputeManager = await ethers.getContractFactory("DisputeManager");
  console.log("Deploying DisputeManager...");
  const disputeManager = await DisputeManager.deploy(
    admin,
    await escrow.getAddress(),
    await verdictRegistry.getAddress(),
    disputeResolver
  );
  await disputeManager.waitForDeployment();
  console.log(`DisputeManager deployed at ${await disputeManager.getAddress()}`);
  await reportDeploymentGas("DisputeManager", disputeManager);

  await waitForTransaction(
    "Grant VerdictRegistry role",
    await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), await verdictRegistry.getAddress())
  );
  await waitForTransaction(
    "Grant DisputeManager role",
    await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), await disputeManager.getAddress())
  );

  const deployedNetwork = await ethers.provider.getNetwork();
  console.log(
    JSON.stringify(
      {
        chainId: deployedNetwork.chainId.toString(),
        deployer: admin,
        bountyEscrow: await escrow.getAddress(),
        verdictRegistry: await verdictRegistry.getAddress(),
        disputeManager: await disputeManager.getAddress(),
        defaultRewardToken: rewardToken,
        relayer,
        disputeResolver,
        gasUsage,
        totalGasUsed: gasUsage.reduce((total, transaction) => total + BigInt(transaction.gasUsed), 0n).toString()
      },
      null,
      2
    )
  );
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
