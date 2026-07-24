import { network } from "hardhat";

const DAY = 24 * 60 * 60;
const MOCK_USDC_MINT_AMOUNT = 1_000_000n * 1_000_000_000_000_000_000n;

type Transaction = { wait: () => Promise<{ gasUsed: bigint } | null> };
type DeployableContract = {
  getAddress: () => Promise<string>;
  waitForDeployment: () => Promise<unknown>;
  deploymentTransaction: () => Transaction | null;
};
type TokenContract = DeployableContract & {
  mint: (to: string, amount: bigint) => Promise<Transaction>;
};
type EscrowContract = DeployableContract & {
  VERDICT_REGISTRY_ROLE: () => Promise<string>;
  DISPUTE_MANAGER_ROLE: () => Promise<string>;
  grantRole: (role: string, account: string) => Promise<Transaction>;
};

const gasUsage: Array<{ label: string; gasUsed: string }> = [];

async function waitForTransaction(label: string, transaction: Transaction) {
  const receipt = await transaction.wait();
  if (receipt === null) throw new Error(`${label} transaction was not mined`);
  gasUsage.push({ label, gasUsed: receipt.gasUsed.toString() });
  console.log(`${label}: ${receipt.gasUsed.toString()} gas used`);
}

async function waitForDeployment(label: string, contract: DeployableContract) {
  await contract.waitForDeployment();
  const deploymentTransaction = contract.deploymentTransaction();
  if (deploymentTransaction === null) throw new Error(`${label} deployment transaction is unavailable`);
  await waitForTransaction(`${label} deployment`, deploymentTransaction);
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const [deployer] = await ethers.getSigners();
  const admin = deployer.address;
  const relayer = admin;
  const disputeResolver = admin;

  const Token = await ethers.getContractFactory("MockUSDC");
  console.log("Deploying local MockUSDC...");
  const token = (await Token.deploy()) as unknown as TokenContract;
  await waitForDeployment("MockUSDC", token);
  const tokenAddress = await token.getAddress();
  await waitForTransaction("MockUSDC mint", await token.mint(admin, MOCK_USDC_MINT_AMOUNT));

  const Escrow = await ethers.getContractFactory("BountyEscrow");
  console.log("Deploying local BountyEscrow...");
  const escrow = (await Escrow.deploy(admin, tokenAddress)) as unknown as EscrowContract;
  await waitForDeployment("BountyEscrow", escrow);
  const escrowAddress = await escrow.getAddress();

  const VerdictRegistry = await ethers.getContractFactory("VerdictRegistry");
  console.log("Deploying local VerdictRegistry...");
  const verdictRegistry = (await VerdictRegistry.deploy(admin, escrowAddress, relayer, 7_000, 3 * DAY)) as unknown as DeployableContract;
  await waitForDeployment("VerdictRegistry", verdictRegistry);
  const verdictRegistryAddress = await verdictRegistry.getAddress();

  const DisputeManager = await ethers.getContractFactory("DisputeManager");
  console.log("Deploying local DisputeManager...");
  const disputeManager = (await DisputeManager.deploy(admin, escrowAddress, verdictRegistryAddress, disputeResolver)) as unknown as DeployableContract;
  await waitForDeployment("DisputeManager", disputeManager);
  const disputeManagerAddress = await disputeManager.getAddress();

  await waitForTransaction("Grant VerdictRegistry role", await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), verdictRegistryAddress));
  await waitForTransaction("Grant DisputeManager role", await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), disputeManagerAddress));

  const deployedNetwork = await ethers.provider.getNetwork();
  const result = {
    chainId: deployedNetwork.chainId.toString(),
    deployer: admin,
    rewardToken: tokenAddress,
    bountyEscrow: escrowAddress,
    verdictRegistry: verdictRegistryAddress,
    disputeManager: disputeManagerAddress,
    relayer,
    disputeResolver,
    mintedToDeployer: MOCK_USDC_MINT_AMOUNT.toString(),
    gasUsage,
    totalGasUsed: gasUsage.reduce((total, transaction) => total + BigInt(transaction.gasUsed), 0n).toString()
  };
  console.log(JSON.stringify(result, null, 2));
  console.log(`FBJ_LOCAL_SANDBOX=${JSON.stringify(result)}`);
}

main().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
