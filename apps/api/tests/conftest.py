"""Keep the test suite independent from the repository/root deployment .env."""

import os
from pathlib import Path


TEST_ENV_FILE = Path(__file__).with_name("test.env")
# The test env file must win even when a developer has Amoy or local-sandbox
# values exported in their terminal session.
SETTINGS_ENV_KEYS = {
    "APP_ENV",
    "FIXTURE_MODE",
    "MONGODB_URI",
    "MONGODB_DATABASE",
    "DATABASE_MODE",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_ALLOWED_REPOSITORIES",
    "GITHUB_APP_ID",
    "GITHUB_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY_B64",
    "GITHUB_CHECK_NAME",
    "AI_PROVIDER",
    "AI_MODEL",
    "AI_TIMEOUT_SECONDS",
    "AI_MAX_DIFF_CHARS",
    "AI_PROMPT_VERSION",
    "GROQ_API_KEY",
    "IPFS_PROVIDER",
    "PINATA_JWT",
    "PINATA_API_URL",
    "IPFS_GATEWAY_URL",
    "AMOY_RPC_URL",
    "CHAIN_ID",
    "BOUNTY_ESCROW_ADDRESS",
    "VERDICT_REGISTRY_ADDRESS",
    "DISPUTE_MANAGER_ADDRESS",
    "REWARD_TOKEN_ADDRESS",
    "RELAYER_PRIVATE_KEY",
    "DISPUTE_RESOLVER_PRIVATE_KEY",
    "CHAIN_EVENT_POLL_SECONDS",
    "CHAIN_EVENT_CONFIRMATIONS",
    "CHAIN_EVENT_START_BLOCK",
}

for key in SETTINGS_ENV_KEYS:
    os.environ.pop(key, None)

os.environ["FBJ_ENV_FILE"] = str(TEST_ENV_FILE)
