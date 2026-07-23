import { network } from "hardhat";

const MOCK_USDC_MINT_AMOUNT = 1_000_000n * 1_000_000_000_000_000_000n;
const MOCK_USDC_DEPLOYMENT_GAS_LIMIT = 700_000n;
const MOCK_USDC_MINT_GAS_LIMIT = 100_000n;

async function main() {
  const { ethers } = await network.getOrCreate();
  const [deployer] = await ethers.getSigners();

  const Token = await ethers.getContractFactory("MockUSDC");
  console.log("Deploying MockUSDC...");
  const token = await Token.deploy({ gasLimit: MOCK_USDC_DEPLOYMENT_GAS_LIMIT });
  await token.waitForDeployment();
  console.log(`MockUSDC deployed at ${await token.getAddress()}`);
  const deploymentTransaction = token.deploymentTransaction();
  if (deploymentTransaction === null) {
    throw new Error("MockUSDC deployment transaction is unavailable");
  }
  const deploymentReceipt = await deploymentTransaction.wait();
  if (deploymentReceipt === null) {
    throw new Error("MockUSDC deployment transaction was not mined");
  }
  console.log(`MockUSDC deployment: ${deploymentReceipt.gasUsed.toString()} gas used`);

  const tokenAddress = await token.getAddress();
  const mintTx = await token.mint(deployer.address, MOCK_USDC_MINT_AMOUNT, {
    gasLimit: MOCK_USDC_MINT_GAS_LIMIT
  });
  const mintReceipt = await mintTx.wait();
  if (mintReceipt === null) {
    throw new Error("MockUSDC mint transaction was not mined");
  }
  console.log(`MockUSDC mint: ${mintReceipt.gasUsed.toString()} gas used`);

  const deployedNetwork = await ethers.provider.getNetwork();
  console.log(
    JSON.stringify(
      {
        chainId: deployedNetwork.chainId.toString(),
        deployer: deployer.address,
        mockUSDC: tokenAddress,
        mintedToDeployer: MOCK_USDC_MINT_AMOUNT.toString(),
        env: `DEFAULT_REWARD_TOKEN=${tokenAddress}`
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
