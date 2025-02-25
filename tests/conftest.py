"""Test configuration for OmniXy."""
import pytest
from src.client import MCPClient

@pytest.fixture
def mcp_client():
    """Create a test MCP client with mock configuration."""
    return MCPClient(
        provider="mock",
        config={
            "mock_responses": True,
            "test_mode": True
        }
    )

@pytest.fixture
def mock_response():
    """Create a mock response for testing."""
    return {
        "id": "test-response-id",
        "choices": [{
            "text": "Test response",
            "finish_reason": "stop"
        }]
    }
