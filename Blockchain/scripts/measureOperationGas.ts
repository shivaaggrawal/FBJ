import { network } from "hardhat";

const DAY = 24 * 60 * 60;
const EVIDENCE_CID = "QmRhT26bHFNVLzWTVmWNLYt9KdcTHgX31LvrcgHapaxihr";
const BOUNTY_AMOUNT = 1_000_000n;

async function receiptGas(transactionPromise: Promise<{ wait: () => Promise<{ gasUsed: bigint } | null> }>) {
  const receipt = await (await transactionPromise).wait();
  if (receipt === null) throw new Error("Transaction was not mined");
  return receipt.gasUsed;
}

async function main() {
  const { ethers } = await network.getOrCreate();
  const [admin, maintainer, relayer, recipient, resolver] = await ethers.getSigners();

  const Token = await ethers.getContractFactory("MockUSDC");
  const token = await Token.deploy();
  await token.waitForDeployment();

  const Escrow = await ethers.getContractFactory("BountyEscrow");
  const escrow = await Escrow.deploy(admin.address, await token.getAddress());
  await escrow.waitForDeployment();

  const Registry = await ethers.getContractFactory("VerdictRegistry");
  const registry = await Registry.deploy(admin.address, await escrow.getAddress(), relayer.address, 7_000, DAY);
  await registry.waitForDeployment();

  const Disputes = await ethers.getContractFactory("DisputeManager");
  const disputes = await Disputes.deploy(admin.address, await escrow.getAddress(), await registry.getAddress(), resolver.address);
  await disputes.waitForDeployment();

  await (await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), await registry.getAddress())).wait();
  await (await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), await disputes.getAddress())).wait();

  async function createFundedBounty(label: string) {
    const bountyId = ethers.keccak256(ethers.toUtf8Bytes(label));
    const latest = await ethers.provider.getBlock("latest");
    if (latest === null) throw new Error("Latest block unavailable");
    await (await token.mint(maintainer.address, BOUNTY_AMOUNT)).wait();
    await (await token.connect(maintainer).approve(await escrow.getAddress(), BOUNTY_AMOUNT)).wait();
    await (await escrow.connect(maintainer).createBounty(bountyId, ethers.ZeroAddress, BOUNTY_AMOUNT, BigInt(latest.timestamp + 10 * DAY))).wait();
    return bountyId;
  }

  const latest = await ethers.provider.getBlock("latest");
  if (latest === null) throw new Error("Latest block unavailable");

  const createBountyId = ethers.keccak256(ethers.toUtf8Bytes("measure-create"));
  await (await token.mint(maintainer.address, BOUNTY_AMOUNT)).wait();
  const approveGas = await receiptGas(token.connect(maintainer).approve(await escrow.getAddress(), BOUNTY_AMOUNT));
  const createBountyGas = await receiptGas(
    escrow.connect(maintainer).createBounty(createBountyId, ethers.ZeroAddress, BOUNTY_AMOUNT, BigInt(latest.timestamp + 10 * DAY))
  );

  const evidenceHash = ethers.keccak256(ethers.toUtf8Bytes("evidence"));
  const releaseBountyId = await createFundedBounty("measure-release");
  const submitVerdictGas = await receiptGas(
    registry.connect(relayer).submitVerdict(releaseBountyId, evidenceHash, EVIDENCE_CID, recipient.address, 9_000)
  );
  await ethers.provider.send("evm_increaseTime", [DAY + 1]);
  await ethers.provider.send("evm_mine", []);
  const releaseBountyGas = await receiptGas(escrow.releaseBounty(releaseBountyId));

  const disputePayBountyId = await createFundedBounty("measure-dispute-pay");
  await receiptGas(registry.connect(relayer).submitVerdict(disputePayBountyId, evidenceHash, EVIDENCE_CID, recipient.address, 9_000));
  const openDisputeGas = await receiptGas(disputes.connect(maintainer).openDispute(disputePayBountyId, EVIDENCE_CID));
  const resolveDisputePayGas = await receiptGas(disputes.connect(resolver).resolveDispute(disputePayBountyId, 1));

  const disputeRefundBountyId = await createFundedBounty("measure-dispute-refund");
  await receiptGas(registry.connect(relayer).submitVerdict(disputeRefundBountyId, evidenceHash, EVIDENCE_CID, recipient.address, 9_000));
  await receiptGas(disputes.connect(maintainer).openDispute(disputeRefundBountyId, EVIDENCE_CID));
  const resolveDisputeRefundGas = await receiptGas(disputes.connect(resolver).resolveDispute(disputeRefundBountyId, 2));

  console.log(
    JSON.stringify(
      {
        approveGas: approveGas.toString(),
        createBountyGas: createBountyGas.toString(),
        submitVerdictGas: submitVerdictGas.toString(),
        releaseBountyGas: releaseBountyGas.toString(),
        openDisputeGas: openDisputeGas.toString(),
        resolveDisputePayGas: resolveDisputePayGas.toString(),
        resolveDisputeRefundGas: resolveDisputeRefundGas.toString()
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
