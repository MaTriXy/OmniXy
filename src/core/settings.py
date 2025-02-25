from typing import Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from pathlib import Path


class APISettings(BaseSettings):
    """API settings for different providers."""

    openai_api_key: Optional[SecretStr] = Field(None, description="OpenAI API key")
    openai_organization: Optional[str] = Field(
        None, description="OpenAI organization ID"
    )

    cohere_api_key: Optional[SecretStr] = Field(None, description="Cohere API key")

    gemini_api_key: Optional[SecretStr] = Field(
        None, description="Google Gemini API key"
    )

    anthropic_api_key: Optional[SecretStr] = Field(
        None, description="Anthropic API key"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "MCP_"
        case_sensitive = False


class ServerSettings(BaseSettings):
    """Server connection settings."""

    default_timeout: int = Field(
        30, description="Default timeout for server connections in seconds"
    )
    default_protocol: str = Field(
        "https", description="Default protocol for server connections"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "MCP_SERVER_"
        case_sensitive = False


class LoggingSettings(BaseSettings):
    """Logging settings."""

    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Logging format",
    )
    file_path: Optional[str] = Field(None, description="Log file path")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "MCP_LOG_"
        case_sensitive = False


class Settings(BaseSettings):
    """Main settings class that combines all settings."""

    # API settings
    api: APISettings = Field(default_factory=APISettings, description="API settings")

    # Server settings
    server: ServerSettings = Field(
        default_factory=ServerSettings, description="Server settings"
    )

    # Logging settings
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging settings"
    )

    # Default provider
    default_provider: Optional[str] = Field(None, description="Default provider to use")

    # Default models for each provider
    default_models: Dict[str, str] = Field(
        default_factory=lambda: {
            "openai": "gpt-4",
            "cohere": "command",
            "gemini": "gemini-1.5-pro",
            "anthropic": "claude-3.7-sonnet-20240620",
        },
        description="Default models for each provider",
    )

    # Test mode
    test_mode: bool = Field(False, description="Whether to run in test mode")

    # Project paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent.parent,
        description="Project root directory",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "MCP_"
        case_sensitive = False


# Create a global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings: The global settings instance
    """
    return settings
