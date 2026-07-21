from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    fixture_mode: bool = True
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "fair_bounty_judge"
    database_mode: str = "memory"
    github_webhook_secret: SecretStr = SecretStr("replace-me")
    github_allowed_repositories_raw: str = Field(default="", validation_alias="GITHUB_ALLOWED_REPOSITORIES")
    github_app_id: str | None = None
    github_installation_id: str | None = None
    github_app_private_key_b64: SecretStr | None = None
    github_check_name: str = "Fair Bounty Judge"
    ai_provider: str = "fixture"
    ai_model: str = "fixture-v1"
    ai_timeout_seconds: int = 45
    ai_max_diff_chars: int = 30_000
    ai_prompt_version: str = "review-v1"
    groq_api_key: SecretStr | None = None
    ipfs_provider: str = "fixture"
    pinata_jwt: SecretStr | None = None
    amoy_rpc_url: str | None = None
    chain_id: int = 80002
    bounty_escrow_address: str | None = None
    verdict_registry_address: str | None = None
    dispute_manager_address: str | None = None
    reward_token_address: str | None = None
    relayer_private_key: SecretStr | None = None

    @property
    def github_allowed_repositories(self) -> list[str]:
        values = [repo.strip() for repo in self.github_allowed_repositories_raw.split(",") if repo.strip()]
        return [repo.removeprefix("https://github.com/").removeprefix("http://github.com/").strip("/") for repo in values]

    @property
    def github_app_enabled(self) -> bool:
        return all((self.github_app_id, self.github_app_private_key_b64))

    def validate_runtime(self) -> None:
        if self.database_mode not in {"memory", "mongodb"}:
            raise ValueError("DATABASE_MODE must be either memory or mongodb")
        if self.ai_provider not in {"fixture", "groq"}:
            raise ValueError("AI_PROVIDER must be either fixture or groq")
        if self.ipfs_provider not in {"fixture", "pinata"}:
            raise ValueError("IPFS_PROVIDER must be either fixture or pinata")
        if self.ai_provider == "groq" and self.groq_api_key is None:
            raise ValueError("GROQ_API_KEY is required when AI_PROVIDER=groq")
        if self.ipfs_provider == "pinata" and self.pinata_jwt is None:
            raise ValueError("PINATA_JWT is required when IPFS_PROVIDER=pinata")
        if not self.fixture_mode and self.database_mode != "mongodb":
            raise ValueError("Non-fixture deployments require DATABASE_MODE=mongodb")
        if not self.fixture_mode:
            required = {
                "GITHUB_WEBHOOK_SECRET": self.github_webhook_secret.get_secret_value() != "replace-me",
                "GITHUB_ALLOWED_REPOSITORIES": bool(self.github_allowed_repositories),
                "AMOY_RPC_URL": bool(self.amoy_rpc_url),
                "BOUNTY_ESCROW_ADDRESS": bool(self.bounty_escrow_address),
                "VERDICT_REGISTRY_ADDRESS": bool(self.verdict_registry_address),
                "DISPUTE_MANAGER_ADDRESS": bool(self.dispute_manager_address),
                "REWARD_TOKEN_ADDRESS": bool(self.reward_token_address),
                "RELAYER_PRIVATE_KEY": self.relayer_private_key is not None,
            }
            missing = [key for key, configured in required.items() if not configured]
            if missing:
                raise ValueError("Missing production configuration: " + ", ".join(missing))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
