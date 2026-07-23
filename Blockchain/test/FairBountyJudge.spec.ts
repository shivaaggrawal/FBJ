import { expect } from "chai";
import { network } from "hardhat";

const DAY = 24 * 60 * 60;
const BOUNTY_ID = "0x0174c006de4202fe494d6d5381e8ff8c998a366b9ccab3012bdd3b52f262f22b";
const SECOND_BOUNTY_ID = "0x1c74c006de4202fe494d6d5381e8ff8c998a366b9ccab3012bdd3b52f262f22b";
const EVIDENCE_CID = "bafybeigdyrzt5n3c7ckpbuq5e7wupzbo3h3sml5fwqnxj46y7a7nt3z3aa";

describe("Fair Bounty Judge contracts", function () {
  async function deploySystem(minimumScore = 7_000, challengePeriod = DAY) {
    const { ethers } = await network.getOrCreate();
    const [admin, maintainer, contributor, relayer, resolver, outsider] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockUSDC");
    const token = await Token.deploy();
    const Escrow = await ethers.getContractFactory("BountyEscrow");
    const escrow = await Escrow.deploy(admin.address, await token.getAddress());
    const Registry = await ethers.getContractFactory("VerdictRegistry");
    const registry = await Registry.deploy(
      admin.address,
      await escrow.getAddress(),
      relayer.address,
      minimumScore,
      challengePeriod
    );
    const Disputes = await ethers.getContractFactory("DisputeManager");
    const disputes = await Disputes.deploy(
      admin.address,
      await escrow.getAddress(),
      await registry.getAddress(),
      resolver.address
    );

    await escrow.grantRole(await escrow.VERDICT_REGISTRY_ROLE(), await registry.getAddress());
    await escrow.grantRole(await escrow.DISPUTE_MANAGER_ROLE(), await disputes.getAddress());
    await token.mint(maintainer.address, 1_000_000n);

    return { ethers, admin, maintainer, contributor, relayer, resolver, outsider, token, escrow, registry, disputes };
  }

  async function createBounty(
    system: Awaited<ReturnType<typeof deploySystem>>,
    bountyId = BOUNTY_ID,
    expiryOffset = 7 * DAY
  ) {
    const latest = await system.ethers.provider.getBlock("latest");
    const amount = 100_000n;
    await system.token.connect(system.maintainer).approve(await system.escrow.getAddress(), amount);
    await system.escrow
      .connect(system.maintainer)
      .createBounty(bountyId, await system.token.getAddress(), amount, BigInt(latest!.timestamp + expiryOffset));
    return amount;
  }

  async function submitPassingVerdict(system: Awaited<ReturnType<typeof deploySystem>>, bountyId = BOUNTY_ID) {
    const evidenceHash = system.ethers.keccak256(system.ethers.toUtf8Bytes('{"score":9000}'));
    await system.registry
      .connect(system.relayer)
      .submitVerdict(bountyId, evidenceHash, EVIDENCE_CID, system.contributor.address, 9_000);
    return evidenceHash;
  }

  it("escrows exact funds and pays an unchallenged passing verdict after the challenge window", async function () {
    const system = await deploySystem();
    const amount = await createBounty(system);
    await submitPassingVerdict(system);

    await expect(system.escrow.releaseBounty(BOUNTY_ID)).to.be.revertedWithCustomError(
      system.escrow,
      "PayoutNotReady"
    );

    await system.ethers.provider.send("evm_increaseTime", [DAY + 1]);
    await system.ethers.provider.send("evm_mine", []);
    await expect(system.escrow.releaseBounty(BOUNTY_ID))
      .to.emit(system.escrow, "BountyPaid")
      .withArgs(BOUNTY_ID, system.contributor.address, amount);
    expect(await system.token.balanceOf(system.contributor.address)).to.equal(amount);
    expect((await system.escrow.getBounty(BOUNTY_ID)).status).to.equal(4n);
  });

  it("uses the configured default token, rejects duplicate IDs, invalid amounts, expiries, and non-token addresses", async function () {
    const system = await deploySystem();
    const now = (await system.ethers.provider.getBlock("latest"))!.timestamp;
    const amount = 100_000n;
    await system.token.connect(system.maintainer).approve(await system.escrow.getAddress(), amount);

    await expect(
      system.escrow.connect(system.maintainer).createBounty(BOUNTY_ID, system.ethers.ZeroAddress, amount, BigInt(now + DAY))
    ).to.emit(system.escrow, "BountyCreated");
    expect((await system.escrow.getBounty(BOUNTY_ID)).token).to.equal(await system.token.getAddress());

    await expect(
      system.escrow.connect(system.maintainer).createBounty(BOUNTY_ID, await system.token.getAddress(), amount, BigInt(now + DAY))
    ).to.be.revertedWithCustomError(system.escrow, "DuplicateBounty");
    await expect(
      system.escrow.connect(system.maintainer).createBounty(SECOND_BOUNTY_ID, await system.token.getAddress(), 0, BigInt(now + DAY))
    ).to.be.revertedWithCustomError(system.escrow, "InvalidAmount");
    await expect(
      system.escrow.connect(system.maintainer).createBounty(SECOND_BOUNTY_ID, await system.token.getAddress(), amount, BigInt(now))
    ).to.be.revertedWithCustomError(system.escrow, "InvalidExpiry");
    await expect(
      system.escrow.connect(system.maintainer).createBounty(SECOND_BOUNTY_ID, system.outsider.address, amount, BigInt(now + DAY))
    ).to.be.revertedWithCustomError(system.escrow, "TokenMustBeContract");
  });

  it("rejects fee-on-transfer reward tokens so escrow accounting remains exact", async function () {
    const system = await deploySystem();
    const FeeToken = await system.ethers.getContractFactory("FeeOnTransferToken");
    const feeToken = await FeeToken.deploy(system.admin.address);
    const amount = 100_000n;
    const now = (await system.ethers.provider.getBlock("latest"))!.timestamp;
    await feeToken.mint(system.maintainer.address, amount);
    await feeToken.connect(system.maintainer).approve(await system.escrow.getAddress(), amount);

    await expect(
      system.escrow
        .connect(system.maintainer)
        .createBounty(BOUNTY_ID, await feeToken.getAddress(), amount, BigInt(now + DAY))
    ).to.be.revertedWithCustomError(system.escrow, "UnsupportedTokenBehavior");
  });

  it("rejects a verdict from an untrusted relayer", async function () {
    const system = await deploySystem();
    await createBounty(system);
    const evidenceHash = system.ethers.keccak256(system.ethers.toUtf8Bytes('{"score":9000}'));
    await expect(
      system.registry
        .connect(system.contributor)
        .submitVerdict(BOUNTY_ID, evidenceHash, EVIDENCE_CID, system.contributor.address, 9_000)
    ).to.be.revertedWithCustomError(system.registry, "AccessControlUnauthorizedAccount");
  });

  it("validates verdict evidence, score, recipient, uniqueness, and challenge timing", async function () {
    const system = await deploySystem();
    await createBounty(system);
    const hash = system.ethers.keccak256(system.ethers.toUtf8Bytes("evidence"));

    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, system.ethers.ZeroHash, EVIDENCE_CID, system.contributor.address, 9_000))
      .to.be.revertedWithCustomError(system.registry, "InvalidEvidenceHash");
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, "bafyNOT-VALID", system.contributor.address, 9_000))
      .to.be.revertedWithCustomError(system.registry, "InvalidEvidenceCid");
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, system.ethers.ZeroAddress, 9_000))
      .to.be.revertedWithCustomError(system.registry, "ZeroAddress");
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, system.contributor.address, 10_001))
      .to.be.revertedWithCustomError(system.registry, "InvalidScore");
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, system.contributor.address, 6_999))
      .to.be.revertedWithCustomError(system.registry, "ScoreBelowThreshold");

    await system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, system.contributor.address, 9_000);
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, system.contributor.address, 9_000))
      .to.be.revertedWithCustomError(system.registry, "VerdictAlreadyExists");

    const shortWindow = await deploySystem();
    await createBounty(shortWindow, BOUNTY_ID, DAY);
    await shortWindow.registry.connect(shortWindow.admin).setChallengePeriod(2 * DAY);
    await expect(shortWindow.registry.connect(shortWindow.relayer).submitVerdict(BOUNTY_ID, hash, EVIDENCE_CID, shortWindow.contributor.address, 9_000))
      .to.be.revertedWithCustomError(shortWindow.registry, "ChallengeWindowExceedsBounty");
  });

  it("allows a maintainer to cancel only an open bounty and refunds an unresolved expired bounty", async function () {
    const system = await deploySystem();
    const amount = await createBounty(system);
    await expect(system.escrow.connect(system.outsider).cancelOpenBounty(BOUNTY_ID))
      .to.be.revertedWithCustomError(system.escrow, "NotMaintainer");
    await expect(system.escrow.connect(system.maintainer).cancelOpenBounty(BOUNTY_ID))
      .to.emit(system.escrow, "BountyRefunded");
    expect((await system.escrow.getBounty(BOUNTY_ID)).status).to.equal(6n);

    await createBounty(system, SECOND_BOUNTY_ID, DAY);
    await system.ethers.provider.send("evm_increaseTime", [DAY + 1]);
    await system.ethers.provider.send("evm_mine", []);
    await expect(system.escrow.refundExpiredBounty(SECOND_BOUNTY_ID))
      .to.emit(system.escrow, "BountyRefunded")
      .withArgs(SECOND_BOUNTY_ID, system.maintainer.address, amount, 5);
  });

  it("locks a disputed bounty until the resolver selects either payout or refund", async function () {
    const system = await deploySystem();
    const amount = await createBounty(system);
    await submitPassingVerdict(system);

    await expect(system.disputes.connect(system.outsider).openDispute(BOUNTY_ID, EVIDENCE_CID))
      .to.be.revertedWithCustomError(system.disputes, "UnauthorizedChallenger");
    await expect(system.disputes.connect(system.maintainer).openDispute(BOUNTY_ID, "bafyINVALID"))
      .to.be.revertedWithCustomError(system.disputes, "InvalidDisputeEvidence");
    await system.disputes.connect(system.maintainer).openDispute(BOUNTY_ID, EVIDENCE_CID);
    await expect(system.escrow.releaseBounty(BOUNTY_ID))
      .to.be.revertedWithCustomError(system.escrow, "InvalidStatus");
    await expect(system.disputes.connect(system.maintainer).openDispute(BOUNTY_ID, EVIDENCE_CID))
      .to.be.revertedWithCustomError(system.disputes, "DisputeAlreadyExists");
    await expect(system.disputes.connect(system.outsider).resolveDispute(BOUNTY_ID, 1))
      .to.be.revertedWithCustomError(system.disputes, "AccessControlUnauthorizedAccount");

    await expect(system.disputes.connect(system.resolver).resolveDispute(BOUNTY_ID, 1))
      .to.emit(system.escrow, "BountyPaid")
      .withArgs(BOUNTY_ID, system.contributor.address, amount);
    expect((await system.disputes.getDispute(BOUNTY_ID)).open).to.equal(false);

    const refundSystem = await deploySystem();
    await createBounty(refundSystem);
    await submitPassingVerdict(refundSystem);
    await refundSystem.disputes.connect(refundSystem.contributor).openDispute(BOUNTY_ID, EVIDENCE_CID);
    await expect(refundSystem.disputes.connect(refundSystem.resolver).resolveDispute(BOUNTY_ID, 2))
      .to.emit(refundSystem.escrow, "BountyRefunded")
      .withArgs(BOUNTY_ID, refundSystem.maintainer.address, amount, 5);
  });

  it("enforces the dispute deadline and admin pause and configuration controls", async function () {
    const system = await deploySystem();
    await createBounty(system);
    await submitPassingVerdict(system);
    await system.ethers.provider.send("evm_increaseTime", [DAY + 1]);
    await system.ethers.provider.send("evm_mine", []);
    await expect(system.disputes.connect(system.maintainer).openDispute(BOUNTY_ID, EVIDENCE_CID))
      .to.be.revertedWithCustomError(system.escrow, "PayoutNotReady");

    await expect(system.escrow.connect(system.outsider).pause())
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");
    await system.escrow.connect(system.admin).pause();
    await expect(system.escrow.releaseBounty(BOUNTY_ID)).to.be.revertedWithCustomError(system.escrow, "EnforcedPause");
    await system.escrow.connect(system.admin).unpause();
    await expect(system.escrow.releaseBounty(BOUNTY_ID)).to.emit(system.escrow, "BountyPaid");

    await expect(system.registry.connect(system.outsider).setMinimumPassingScoreBps(5_000))
      .to.be.revertedWithCustomError(system.registry, "AccessControlUnauthorizedAccount");
    await expect(system.registry.connect(system.admin).setMinimumPassingScoreBps(10_001))
      .to.be.revertedWithCustomError(system.registry, "InvalidScore");
    await system.registry.connect(system.admin).setMinimumPassingScoreBps(8_000);
    await expect(system.registry.connect(system.admin).setChallengePeriod(0))
      .to.be.revertedWithCustomError(system.registry, "InvalidChallengePeriod");
    await system.registry.connect(system.admin).setChallengePeriod(DAY / 2);
  });

  it("protects administrative paths and exposes safe empty reads", async function () {
    const system = await deploySystem();
    const ReplacementToken = await system.ethers.getContractFactory("MockUSDC");
    const replacementToken = await ReplacementToken.deploy();

    await expect(system.escrow.getBounty(BOUNTY_ID)).to.be.revertedWithCustomError(system.escrow, "BountyNotFound");
    expect((await system.registry.getVerdict(BOUNTY_ID)).exists).to.equal(false);
    expect((await system.disputes.getDispute(BOUNTY_ID)).open).to.equal(false);
    await expect(system.escrow.connect(system.outsider).setDefaultRewardToken(await replacementToken.getAddress()))
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");
    await expect(system.escrow.connect(system.admin).setDefaultRewardToken(system.outsider.address))
      .to.be.revertedWithCustomError(system.escrow, "TokenMustBeContract");
    await system.escrow.connect(system.admin).setDefaultRewardToken(await replacementToken.getAddress());
    expect(await system.escrow.defaultRewardToken()).to.equal(await replacementToken.getAddress());

    await expect(system.escrow.connect(system.outsider).recordVerdict(BOUNTY_ID, system.contributor.address, 1))
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");
    await expect(system.escrow.connect(system.outsider).markDisputed(BOUNTY_ID))
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");
    await expect(system.escrow.connect(system.outsider).resolveDisputeToRecipient(BOUNTY_ID))
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");
    await expect(system.escrow.connect(system.outsider).resolveDisputeToMaintainer(BOUNTY_ID))
      .to.be.revertedWithCustomError(system.escrow, "AccessControlUnauthorizedAccount");

    await system.registry.connect(system.admin).pause();
    await expect(system.registry.connect(system.relayer).submitVerdict(BOUNTY_ID, system.ethers.keccak256("0x01"), EVIDENCE_CID, system.contributor.address, 9_000))
      .to.be.revertedWithCustomError(system.registry, "EnforcedPause");
    await system.registry.connect(system.admin).unpause();
    await system.disputes.connect(system.admin).pause();
    await expect(system.disputes.connect(system.maintainer).openDispute(BOUNTY_ID, EVIDENCE_CID))
      .to.be.revertedWithCustomError(system.disputes, "EnforcedPause");
    await system.disputes.connect(system.admin).unpause();
  });

  it("fails deployment when dependency addresses are malformed", async function () {
    const { ethers } = await network.getOrCreate();
    const [admin, outsider] = await ethers.getSigners();
    const Escrow = await ethers.getContractFactory("BountyEscrow");
    await expect(Escrow.deploy(admin.address, ethers.ZeroAddress)).to.be.revertedWithCustomError(Escrow, "ZeroAddress");
    await expect(Escrow.deploy(admin.address, outsider.address)).to.be.revertedWithCustomError(Escrow, "TokenMustBeContract");

    const Token = await ethers.getContractFactory("MockUSDC");
    const token = await Token.deploy();
    const validEscrow = await Escrow.deploy(admin.address, await token.getAddress());
    const Registry = await ethers.getContractFactory("VerdictRegistry");
    await expect(Registry.deploy(admin.address, outsider.address, admin.address, 7_000, DAY))
      .to.be.revertedWithCustomError(Registry, "EscrowMustBeContract");
    const validRegistry = await Registry.deploy(admin.address, await validEscrow.getAddress(), admin.address, 7_000, DAY);
    const Disputes = await ethers.getContractFactory("DisputeManager");
    await expect(Disputes.deploy(admin.address, outsider.address, await validRegistry.getAddress(), admin.address))
      .to.be.revertedWithCustomError(Disputes, "DependencyMustBeContract");
  });
});
