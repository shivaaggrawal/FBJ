from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    fixture_mode: bool = True
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "fair_bounty_judge"
    database_mode: str = "memory"
    github_webhook_secret: SecretStr = SecretStr("replace-me")
    github_allowed_repositories: list[str] = Field(default_factory=list)
    ai_provider: str = "fixture"
    ai_model: str = "fixture-v1"
    ipfs_provider: str = "fixture"
    amoy_rpc_url: str | None = None
    chain_id: int = 80002
    bounty_escrow_address: str | None = None
    verdict_registry_address: str | None = None
    dispute_manager_address: str | None = None
    reward_token_address: str | None = None
    relayer_private_key: SecretStr | None = None

    @field_validator("github_allowed_repositories", mode="before")
    @classmethod
    def parse_repositories(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [repo.strip() for repo in value.split(",") if repo.strip()]
        return value

    def validate_runtime(self) -> None:
        if self.database_mode not in {"memory", "mongodb"}:
            raise ValueError("DATABASE_MODE must be either memory or mongodb")
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
