from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YOUSIM_", env_file=".env", extra="ignore")

    app_name: str = "YouSim API"
    environment: str = "dev"
    model_version: str = "ml-ranker-v1"
    policy_version: str = "conservative-policy-v1"
    economic_assumptions_version: str = "ca-2026q1"
    monte_carlo_paths: int = Field(default=600, ge=100, le=5000)
    monte_carlo_seed: int = 42
    preview_ttl_minutes: int = 15
    required_bearer_token: str = "yousim-demo-token"


settings = Settings()
