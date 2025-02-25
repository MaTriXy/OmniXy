"""Unit tests for the MCP layer."""
import pytest
from src.core.mcp_layer import MCPLayer

def test_mcp_layer_initialization():
    """Test MCP layer initialization."""
    layer = MCPLayer()
    assert layer is not None
    assert hasattr(layer, 'process_request')

def test_mcp_layer_protocol_validation():
    """Test MCP protocol validation."""
    layer = MCPLayer()
    valid_request = {
        "messages": [{"role": "user", "content": "test"}],
        "model": "test-model"
    }
    assert layer.validate_request(valid_request) is True

    invalid_request = {"invalid": "format"}
    with pytest.raises(ValueError):
        layer.validate_request(invalid_request)

def test_mcp_layer_response_format():
    """Test MCP response formatting."""
    layer = MCPLayer()
    response = layer.format_response({
        "text": "test response",
        "usage": {"total_tokens": 10}
    })
    assert "text" in response
    assert "usage" in response
    assert response["usage"]["total_tokens"] == 10
