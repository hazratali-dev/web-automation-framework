from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration. Values come from .env.local (dev) or
    real environment variables (prod) — see ARCHITECTURE.md §Appendix A / §6."""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"  # "local" or "production"
    database_url: str = "sqlite:///local.db"
    log_level: str = "INFO"

    # Fernet key for encrypting proxy passwords at rest (§8). Dev-only default
    # below is NOT secret-manager-grade — prod must supply its own via env/Vault.
    fernet_key: str = "uaXeKLHzkmKDLcsQ2ZW8ARsUwKV7C7Op-TAPJfFr-Go="


@lru_cache
def get_settings() -> Settings:
    return Settings()
