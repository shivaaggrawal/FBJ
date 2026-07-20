import { network } from "hardhat";

const DAY = 24 * 60 * 60;

async function main() {
  const { ethers } = await network.getOrCreate();
  const [deployer] = await ethers.getSigners();

  const rewardToken = process.env.DEFAULT_REWARD_TOKEN;
  if (!rewardToken) throw new Error("DEFAULT_REWARD_TOKEN must be set");

  const admin = deployer.address;
  const relayer = process.env.RELAYER_ADDRESS ?? admin;
  const disputeResolver = process.env.DISPUTE_RESOLVER_ADDRESS ?? admin;

  const Escrow = await ethers.getContractFactory("BountyEscrow");
  const escrow = await Escrow.deploy(admin, rewardToken);
  await escrow.waitForDeployment();

  const VerdictRegistry = await ethers.getContractFactory("VerdictRegistry");
  const verdictRegistry = await VerdictRegistry.deploy(
    admin,
    await escrow.getAddress(),
    7_000,
    3 * DAY
  );
  await verdictRegistry.waitForDeployment();

  const DisputeManager = await ethers.getContractFactory("DisputeManager");
  const disputeManager = await DisputeManager.deploy(
    admin,
    await escrow.getAddress(),
    await verdictRegistry.getAddress()
  );
  await disputeManager.waitForDeployment();

  await (
    await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), await verdictRegistry.getAddress())
  ).wait();
  await (
    await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), await disputeManager.getAddress())
  ).wait();
  await (await verdictRegistry.grantRole(await verdictRegistry.RELAYER_ROLE(), relayer)).wait();
  await (await disputeManager.grantRole(await disputeManager.DISPUTE_ROLE(), disputeResolver)).wait();

  const deployedNetwork = await ethers.provider.getNetwork();
  console.log(
    JSON.stringify(
      {
        chainId: deployedNetwork.chainId.toString(),
        deployer: admin,
        bountyEscrow: await escrow.getAddress(),
        verdictRegistry: await verdictRegistry.getAddress(),
        disputeManager: await disputeManager.getAddress(),
        relayer,
        disputeResolver
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
