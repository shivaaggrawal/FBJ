import "dotenv/config";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";
import { defineConfig } from "hardhat/config";

const privateKey = process.env.DEPLOYER_PRIVATE_KEY;
const amoyRpcUrl = process.env.AMOY_RPC_URL;

export default defineConfig({
  plugins: [hardhatToolboxMochaEthers],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
        settings: {
          optimizer: { enabled: true, runs: 200 },
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
