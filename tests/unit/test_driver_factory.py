"""Unit tests for the driver factory."""

import pytest
from src.drivers.driver_factory import DriverFactory, AnthropicDriverConfig
from src.drivers.openai_driver import OpenAIDriver
from src.drivers.cohere_driver import CohereDriver
from src.drivers.gemini_driver import GeminiDriver
from src.drivers.anthropic_driver import AnthropicDriver
from src.drivers.local_llm_driver import LocalLLMDriver


class TestDriverFactory:
    """Test suite for the driver factory."""

    def test_init(self):
        """Test factory initialization."""
        factory = DriverFactory()

        # Check that all expected drivers are registered
        assert "openai" in factory.drivers
        assert "cohere" in factory.drivers
        assert "gemini" in factory.drivers
        assert "anthropic" in factory.drivers
        assert "local" in factory.drivers
        assert "mock" in factory.drivers

        # Check that driver classes are correct
        assert factory.drivers["openai"] == OpenAIDriver
        assert factory.drivers["cohere"] == CohereDriver
        assert factory.drivers["gemini"] == GeminiDriver
        assert factory.drivers["anthropic"] == AnthropicDriver
        assert factory.drivers["local"] == LocalLLMDriver

        # Check that config classes are registered
        assert "openai" in factory.config_classes
        assert "cohere" in factory.config_classes
        assert "gemini" in factory.config_classes
        assert "anthropic" in factory.config_classes
        assert "local" in factory.config_classes

    def test_register_driver(self):
        """Test registering a new driver."""
        factory = DriverFactory()

        # Create a dummy driver class
        class DummyDriver:
            def __init__(self, config=None):
                self.config = config or {}

        # Register the dummy driver
        factory.register_driver("dummy", DummyDriver)

        # Check that the driver was registered
        assert "dummy" in factory.drivers
        assert factory.drivers["dummy"] == DummyDriver

    def test_create_driver(self):
        """Test creating drivers with different configurations."""
        factory = DriverFactory()

        # Test creating an OpenAI driver
        openai_driver = factory.create_driver("openai", {"api_key": "test-key"})
        assert isinstance(openai_driver, OpenAIDriver)

        # Test creating a Cohere driver
        cohere_driver = factory.create_driver("cohere", {"api_key": "test-key"})
        assert isinstance(cohere_driver, CohereDriver)

        # Test creating a Gemini driver
        gemini_driver = factory.create_driver("gemini", {"api_key": "test-key"})
        assert isinstance(gemini_driver, GeminiDriver)

        # Test creating an Anthropic driver
        anthropic_driver = factory.create_driver("anthropic", {"api_key": "test-key"})
        assert isinstance(anthropic_driver, AnthropicDriver)

        # Test creating a local driver
        local_driver = factory.create_driver("local", {"model_path": "test-path"})
        assert isinstance(local_driver, LocalLLMDriver)

    def test_config_validation(self):
        """Test configuration validation."""
        factory = DriverFactory()

        # Test valid Anthropic config
        config = AnthropicDriverConfig(api_key="test-key")
        assert config.api_key == "test-key"
        assert config.test_mode is False

        # Test with test mode
        config = AnthropicDriverConfig(api_key="test-key", test_mode=True)
        assert config.api_key == "test-key"
        assert config.test_mode is True

    def test_invalid_provider(self):
        """Test error handling for invalid providers."""
        factory = DriverFactory()

        # Test with non-existent provider
        with pytest.raises(ValueError):
            factory.create_driver("non-existent-provider")
