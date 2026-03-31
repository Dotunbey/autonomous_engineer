import logging
from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field

logger = logging.getLogger(__name__)


class AppConfig(BaseSettings):
    """
    Centralized configuration management for the autonomous engineer platform.
    Automatically loads variables from the environment or a .env file.
    """
    
    environment: str = Field("development", env="ENV")
    api_key: str = Field("default-dev-key", env="AGENT_API_KEY")
    
    # Infrastructure
    redis_url: str = Field("redis://localhost:6379/0", env="CELERY_BROKER_URL")
    sqlite_db_path: str = Field("data/agent_data.db", env="SQLITE_DB_PATH")
    
    # LLM Settings
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    default_model: str = Field("llama3-70b-8192", env="DEFAULT_MODEL")
    
    # Observability
    enable_tracing: bool = Field(False, env="ENABLE_TRACING")
    metrics_port: int = Field(9090, env="METRICS_PORT")

    class Config:
        """Pydantic V1 config class for env file settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_config() -> AppConfig:
    """
    Retrieves the global configuration instance. 
    Uses lru_cache to ensure the configuration is only parsed once.
    
    Returns:
        AppConfig: The singleton configuration object.
    """
    logger.info("Loading application configuration.")
    return AppConfig()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = get_config()
    logger.info(f"Loaded config for environment: {config.environment}")
    logger.info(f"Using Redis URL: {config.redis_url}")
