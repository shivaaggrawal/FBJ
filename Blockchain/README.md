# Fair Bounty Judge - Blockchain Layer

This is the custody and audit-proof layer for Fair Bounty Judge (FBJ). It accepts ERC-20 bounties, anchors a reviewed AI evidence bundle, provides a challenge window, and releases or refunds escrowed funds.

The backend remains responsible for GitHub webhooks, PR retrieval, LangGraph evaluation, deterministic consensus, canonical JSON serialization, IPFS/Pinata upload, and event indexing. It must never give an AI agent a private key or direct blockchain access. Only a backend relayer with `RELAYER_ROLE` can publish a verdict.

## Contract model

| Contract | Purpose | May move funds |
| --- | --- | --- |
| `BountyEscrow` | Holds ERC-20 bounties and tracks lifecycle state. | Yes, and only this contract. |
| `VerdictRegistry` | Anchors `keccak256(evidenceBytes)`, CID, score, recipient, and challenge deadline. | No. |
| `DisputeManager` | Lets either payout party open a challenge and lets an adjudicator resolve it. | No. |

Each bounty has its own token address. Updating `defaultRewardToken` only changes the default for future bounties; it cannot redirect funds already held in escrow. The implementation rejects fee-on-transfer tokens, because the recorded reward must equal the amount actually received.

## Lifecycle

```text
maintainer -> createBounty -> BountyEscrow(Open)
relayer -> submitVerdict -> VerdictRegistry + BountyEscrow(VerdictSubmitted)
maintainer or recipient -> openDispute -> BountyEscrow(Challenged)
resolver -> resolveDispute -> recipient payout OR maintainer refund
no challenge -> releaseBounty after releaseAt -> recipient payout
```

The relayer cannot release a bounty. The dispute resolver cannot create or mutate verdict evidence. Bounties without a verdict can be cancelled by their maintainer or refunded by anyone after expiry. A normal unchallenged payout must occur before the bounty expiry; a disputed bounty remains resolvable after expiry because it was locked before its deadline.

## Evidence bundle

Build a deterministic JSON object before its IPFS upload. Use stable key ordering, no non-deterministic timestamps inside derived scores, and hash the exact UTF-8 bytes that are uploaded.

```json
{
  "schemaVersion": 1,
  "bountyId": "0x...",
  "repository": "owner/repository",
  "prNumber": 42,
  "commitSha": "...",
  "evaluatedAt": "2026-07-18T00:00:00.000Z",
  "finalScoreBps": 8600,
  "confidenceBps": 9100,
  "agentScores": [{ "agent": "security", "scoreBps": 8700 }],
  "reasoning": "..."
}
```

The backend calculates `evidenceHash = keccak256(evidenceBytes)`, uploads those same bytes to IPFS, retains the CID, and calls `submitVerdict`. The provided `scripts/submitVerdict.ts` performs the same byte-level Keccak calculation for a prepared local bundle. Its SHA-256 output is only an operator convenience; the on-chain commitment is Keccak-256.

## Roles

| Role | Holder | Authority |
| --- | --- | --- |
| `DEFAULT_ADMIN_ROLE` | Multisig in production | Configure roles, token default, scoring rules, and pause controls. |
| `RELAYER_ROLE` | Backend relayer | Submit a passing evidence bundle. |
| `VERDICT_REGISTRY_ROLE` | `VerdictRegistry` contract | Record recipient and release deadline in escrow. |
| `DISPUTE_MANAGER_ROLE` | `DisputeManager` contract | Lock and resolve challenged escrow. |
| `DISPUTE_ROLE` | Adjudicator multisig/service | Resolve an open dispute. |

Transfer the default admin role to a multisig before production. A production deployment should also use a separate relayer key, monitoring for every event, a funded incident-response process for `pause`, and a third-party audit before mainnet custody.

## Local development

```bash
copy ..\.env.example ..\.env
npm.cmd install
npm.cmd run compile
npm.cmd test
```

The initial deployment policy is a 70% minimum score and a three-day challenge period. Both are admin-configurable, though new settings affect only future verdict submissions. Set `AMOY_RPC_URL`, `DEPLOYER_PRIVATE_KEY`, `RELAYER_ADDRESS`, and `DISPUTE_RESOLVER_ADDRESS` in the repository-root `.env`, then deploy with:

```bash
npm.cmd run deploy:amoy
```

`DEFAULT_REWARD_TOKEN` is required for the protocol deployment, which avoids an accidental token deployment and mint. To create a demo token deliberately, run `npm.cmd run deploy:mock-usdc:amoy` once, save its address as `DEFAULT_REWARD_TOKEN`, then run `deploy:amoy`. The deploy command prints the exact `chainId`, token address, and the three contract addresses plus per-transaction gas usage. Retain that JSON in the backend configuration; all later commands require the relevant deployed address.

If a prior Amoy attempt already deployed `BountyEscrow`, do not deploy it again. Set `BOUNTY_ESCROW_ADDRESS` and `DEFAULT_REWARD_TOKEN`, leave missing contract addresses blank, then run:

```bash
npm.cmd run deploy:resume:amoy
npm.cmd run roles:check:amoy
```

The resume command deploys only the missing registry/manager contracts, grants only missing roles, and prints the repository-root `.env` address values. The role check is read-only and should report `"ready": true` before switching the backend out of fixture mode.

To deploy only the test token on the configured network:

```bash
npm.cmd run deploy:mock-usdc -- --network amoy
```

## Contract integration commands

These commands use the wallet in `DEPLOYER_PRIVATE_KEY`. In production, run each command from the role-holder service or replace the script signer with the appropriate managed signer. All values are validated before the transaction is broadcast.

```bash
# Approve the ERC-20 and create a bounty. Use the zero address to select the escrow default token.
npm.cmd run bounty:create -- <escrow> <token-or-0x0000000000000000000000000000000000000000> <bounty-id> <amount> <expiry-unix>

# Relayer: hash the exact uploaded evidence bytes and submit its IPFS CID.
npm.cmd run bounty:submit-verdict -- <registry> <bounty-id> <cid> <recipient> <score-bps> <evidence.json>

# Anyone can release an unchallenged bounty once its challenge deadline passes.
npm.cmd run bounty:release -- <escrow> <bounty-id>

# Maintainer or selected recipient: open a challenge before the deadline.
npm.cmd run bounty:open-dispute -- <dispute-manager> <bounty-id> <challenge-evidence-cid>

# Dispute-role holder: pay contributor or refund maintainer.
npm.cmd run bounty:resolve-dispute -- <dispute-manager> <bounty-id> <pay|refund>
```

The `bounty:submit-verdict` command is the backend integration boundary. Keep the relayer key in a managed secret store, give the AI service no wallet access, verify the CID remains pinned, and feed only the prepared evidence bundle to the relayer queue.

Polygon Amoy uses chain ID `80002` and POL for gas. When `DEFAULT_REWARD_TOKEN` is provided, it must be an ERC-20 deployed on Amoy; use a test token, not production USDC.

## Security notes and next milestones

- All ERC-20 transfers use `SafeERC20`; state changes precede external token calls and payout paths are protected by `ReentrancyGuard`.
- Bounty IDs are immutable and unique. Verdict submission is one-time, role-gated, score-bounded, CID shape-checked, and tied to an existing unexpired bounty.
- The CID validation supports common CIDv0 (`Qm...`) and CIDv1 (`bafy...`) forms. It is a format guard, not a guarantee that IPFS content remains pinned; Pinata retention and the backend’s hash verification provide that guarantee.
- The current dispute process is trusted adjudication. Do not claim it is decentralized until a DAO, arbitration system, or equivalent governance process replaces `DISPUTE_ROLE`.
- Before mainnet, add EIP-712 signed verdict intents, replay-safe relayer queues, formal incident runbooks, invariant/fuzz tests, independent auditing, and a governance decision on upgradeability. The first custody deployment should remain non-upgradeable unless a separately reviewed proxy governance design is approved.
