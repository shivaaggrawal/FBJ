import { config as loadEnvironment } from "dotenv";
import { fileURLToPath } from "node:url";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";

// All applications and scripts use the single repository-root .env file.
loadEnvironment({ path: fileURLToPath(new URL("../.env", import.meta.url)) });

const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
const amoyRpcUrl = process.env.AMOY_RPC_URL;

export default defineConfig({
  plugins: [hardhatToolboxMochaEthers],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
        settings: {
          // Deployment cost matters more than repeated on-chain execution for this MVP.
          optimizer: { enabled: true, runs: 1 },
          evmVersion: "paris"
        }
      }
    }
  },
  networks: amoyRpcUrl
    ? {
        amoy: {
          type: "http",
          chainType: "l1",
          url: amoyRpcUrl,
          accounts: privateKey ? [privateKey] : []
        }
      }
    : {},
  test: {
    mocha: {
      timeout: 40_000
    }
  }
});
