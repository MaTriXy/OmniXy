"""Factory for creating MCP drivers."""

from typing import Dict, Optional, Type, Any
from pydantic import BaseModel, Field

from src.drivers.cohere_driver import CohereDriver
from src.drivers.gemini_driver import GeminiDriver
from src.drivers.openai_driver import OpenAIDriver
from src.drivers.local_llm_driver import LocalLLMDriver
from src.drivers.anthropic_driver import AnthropicDriver


class BaseDriverConfig(BaseModel):
    """Base configuration for all drivers."""

    test_mode: bool = Field(False, description="Whether to run in test mode")
    mock_responses: bool = Field(False, description="Whether to return mock responses")


class OpenAIDriverConfig(BaseDriverConfig):
    """Configuration for OpenAI driver."""

    api_key: Optional[str] = Field(None, description="OpenAI API key")
    organization: Optional[str] = Field(None, description="OpenAI organization ID")


class CohereDriverConfig(BaseDriverConfig):
    """Configuration for Cohere driver."""

    api_key: Optional[str] = Field(None, description="Cohere API key")


class GeminiDriverConfig(BaseDriverConfig):
    """Configuration for Google Gemini driver."""

    api_key: Optional[str] = Field(None, description="Google API key")


class AnthropicDriverConfig(BaseDriverConfig):
    """Configuration for Anthropic driver."""

    api_key: Optional[str] = Field(None, description="Anthropic API key")


class LocalLLMDriverConfig(BaseDriverConfig):
    """Configuration for local LLM driver."""

    model_path: Optional[str] = Field(None, description="Path to the local model")


class DriverFactory:
    """Factory class for creating MCP drivers."""

    def __init__(self):
        """Initialize the driver factory with default drivers."""
        self.drivers = {
            "cohere": CohereDriver,
            "gemini": GeminiDriver,
            "openai": OpenAIDriver,
            "anthropic": AnthropicDriver,
            "local": LocalLLMDriver,
            "mock": LocalLLMDriver,
        }

        # Map provider names to their config classes
        self.config_classes = {
            "cohere": CohereDriverConfig,
            "gemini": GeminiDriverConfig,
            "openai": OpenAIDriverConfig,
            "anthropic": AnthropicDriverConfig,
            "local": LocalLLMDriverConfig,
            "mock": BaseDriverConfig,
        }

    def register_driver(self, provider_name: str, driver_class: Type):
        """Register a driver for a provider.

        Args:
            provider_name (str): Name of the provider
            driver_class: Driver class to use for this provider
        """
        self.drivers[provider_name] = driver_class

    def create_driver(
        self, provider_name: str, provider_config: Optional[Dict[str, Any]] = None
    ):
        """Create a driver for a provider with optional configuration.

        Args:
            provider_name (str): Name of the provider
            provider_config (dict, optional): Configuration for the provider

        Returns:
            BaseDriver: Appropriate driver instance

        Raises:
            ValueError: If the provider is not supported
        """
        if provider_config is None:
            provider_config = {}

        if provider_name not in self.drivers:
            raise ValueError(f"Unsupported provider: {provider_name}")

        # Validate configuration using Pydantic
        config_class = self.config_classes.get(provider_name, BaseDriverConfig)
        validated_config = config_class(**provider_config)

        driver_class = self.drivers[provider_name]
        return driver_class(validated_config.model_dump())
