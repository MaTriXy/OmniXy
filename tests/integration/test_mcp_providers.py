"""Integration tests for MCP providers."""

import os
import pytest
from src.client import MCPClient
from src.core.response import MCPResponse


@pytest.mark.integration
class TestMCPProviders:
    """Test suite for MCP provider integration."""

    def test_openai_integration(self):
        """Test OpenAI provider integration."""
        client = MCPClient(provider="openai")
        response = client.complete(
            messages=[{"role": "user", "content": "Test message"}], model="o3-mini"
        )
        assert response is not None
        # Handle both MCPResponse and dict formats
        if isinstance(response, MCPResponse):
            assert response.text is not None
        else:
            assert "choices" in response or "text" in response

    def test_cohere_integration(self):
        """Test Cohere provider integration."""
        client = MCPClient(provider="cohere")
        response = client.complete(
            messages=[{"role": "user", "content": "Test message"}],
            model="command-r7b-12-2024",
        )
        assert response is not None
        # Handle both MCPResponse and dict formats
        if isinstance(response, MCPResponse):
            assert response.text is not None
        else:
            assert "text" in response or "generations" in response

    def test_gemini_integration(self):
        """Test Gemini provider integration."""
        client = MCPClient(provider="gemini")
        response = client.complete(
            messages=[{"role": "user", "content": "Test message"}],
            model="gemini-2.0-flash",
        )
        assert response is not None
        # Handle both MCPResponse and dict formats
        if isinstance(response, MCPResponse):
            assert response.text is not None
        else:
            assert "candidates" in response or "text" in response

    def test_anthropic_integration(self):
        """Test Anthropic provider integration."""
        client = MCPClient(provider="anthropic")
        response = client.complete(
            messages=[{"role": "user", "content": "Test message"}],
            model="claude-3.7-sonnet",
        )
        assert response is not None
        # Handle both MCPResponse and dict formats
        if isinstance(response, MCPResponse):
            assert response.text is not None
        else:
            assert "content" in response or "text" in response

    def test_provider_switching(self):
        """Test switching between providers."""
        client = MCPClient(provider="openai")
        response1 = client.complete(
            messages=[{"role": "user", "content": "Test message"}], model="o3-mini"
        )

        # Register the cohere provider before switching to it
        client.register_provider("cohere")
        client.set_provider("cohere")
        response2 = client.complete(
            messages=[{"role": "user", "content": "Test message"}],
            model="command-r7b-12-2024",
        )

        assert response1 is not None
        assert response2 is not None
        assert response1 != response2


@pytest.mark.integration
class TestProviderFeatures:
    """Test suite for provider-specific features."""

    def test_streaming_support(self):
        """Test streaming support across providers."""
        providers = ["openai", "cohere", "gemini", "anthropic"]

        for provider in providers:
            client = MCPClient(provider=provider)
            model = "o3-mini"
            if provider == "cohere":
                model = "command"
            elif provider == "gemini":
                model = "gemini-2.0-flash"
            elif provider == "anthropic":
                model = "claude-3-haiku-20240307"

            stream = client.complete(
                messages=[{"role": "user", "content": "Test message"}],
                model=model,
                stream=True,
            )

            chunks = list(stream)
            assert len(chunks) > 0

    def test_error_handling(self):
        """Test error handling across providers."""
        client = MCPClient(provider="openai")

        with pytest.raises(Exception):
            client.complete(
                messages=[{"role": "user", "content": "Test message"}],
                model="non-existent-model",
            )

        # Create a new client with the anthropic provider
        client = MCPClient(provider="anthropic")
        with pytest.raises(Exception):
            client.complete(
                messages=[{"role": "user", "content": "Test message"}],
                model="non-existent-model",
            )
