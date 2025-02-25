"""Unit tests for request handling."""

import pytest
from src.core.request import MCPRequest, Message


def test_request_creation():
    """Test creating an MCP request."""
    request = MCPRequest(
        messages=[{"role": "user", "content": "test"}],
        model="gemini-2.0-flash",
        temperature=0.7,
    )
    assert request.messages[0].role == "user"
    assert request.model == "gemini-2.0-flash"
    assert request.temperature == 0.7


def test_request_validation():
    """Test request validation."""
    # Valid request
    request = MCPRequest(
        messages=[{"role": "user", "content": "test"}], model="gemini-2.0-flash"
    )
    assert request.validate() is True

    # Invalid request - empty messages
    with pytest.raises(ValueError):
        MCPRequest(messages=[], model="gemini-2.0-flash")

    # Invalid request - missing model
    with pytest.raises(ValueError):
        MCPRequest(messages=[{"role": "user", "content": "test"}])


def test_request_serialization():
    """Test request serialization."""
    request = MCPRequest(
        messages=[{"role": "user", "content": "test"}],
        model="gemini-2.0-flash",
        temperature=0.7,
        max_tokens=100,
    )
    serialized = request.to_dict()
    assert serialized["messages"] == [{"role": "user", "content": "test"}]
    assert serialized["model"] == "gemini-2.0-flash"
    assert serialized["temperature"] == 0.7
    assert serialized["max_tokens"] == 100


def test_request_from_dict():
    """Test creating request from dictionary."""
    data = {
        "messages": [{"role": "user", "content": "test"}],
        "model": "gemini-2.0-flash",
        "temperature": 0.7,
    }
    request = MCPRequest.from_dict(data)
    # Convert messages to dictionaries for comparison
    messages_dict = [{"role": m.role, "content": m.content} for m in request.messages]
    assert messages_dict == data["messages"]
    assert request.model == data["model"]
    assert request.temperature == data["temperature"]


def test_request_stream_handling():
    """Test request stream handling."""
    request = MCPRequest(
        messages=[{"role": "user", "content": "test"}],
        model="gemini-2.0-flash",
        stream=True,
    )
    assert request.stream is True
    assert request.validate() is True
