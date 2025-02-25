"""Unit tests for response handling."""

import pytest
from src.core.response import MCPResponse


def test_response_creation():
    """Test creating an MCP response."""
    response = MCPResponse(
        text="Test response", usage={"total_tokens": 10}, model="test-model"
    )
    assert response.text == "Test response"
    assert response.usage["total_tokens"] == 10
    assert response.model == "test-model"


def test_response_validation():
    """Test response validation."""
    # Valid response
    response = MCPResponse(text="Test response", usage={"total_tokens": 10})
    assert response.validate() is True

    # Invalid response - empty text
    with pytest.raises(ValueError):
        MCPResponse(text="", usage={"total_tokens": 10})


def test_response_serialization():
    """Test response serialization."""
    response = MCPResponse(
        text="Test response",
        usage={"total_tokens": 10},
        model="test-model",
        finish_reason="stop",
    )
    serialized = response.to_dict()
    assert serialized["text"] == "Test response"
    assert serialized["usage"]["total_tokens"] == 10
    assert serialized["model"] == "test-model"
    assert serialized["finish_reason"] == "stop"


def test_response_from_dict():
    """Test creating response from dictionary."""
    data = {
        "text": "Test response",
        "usage": {"total_tokens": 10},
        "model": "test-model",
    }
    response = MCPResponse.from_dict(data)
    assert response.text == data["text"]
    assert response.usage == data["usage"]
    assert response.model == data["model"]


def test_response_stream_chunk():
    """Test response streaming chunk handling."""
    chunk = MCPResponse(text="partial ", usage={"total_tokens": 5}, is_chunk=True)
    assert chunk.is_chunk is True
    assert chunk.validate() is True


def test_response_metadata():
    """Test response metadata handling."""
    response = MCPResponse(
        text="Test response",
        usage={"total_tokens": 10},
        metadata={"latency_ms": 150, "provider": "test-provider"},
    )
    assert response.metadata["latency_ms"] == 150
    assert response.metadata["provider"] == "test-provider"
