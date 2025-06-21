"""Unit tests for MCP Response Pydantic models based on JSON-RPC."""

import pytest
from pydantic import ValidationError

from src.core.response import (
    JSONRPCResponse,
    JSONRPCErrorResponse,
    InitializeResult,
    ServerCapabilities,
    Implementation as ServerImplementation, # Alias to avoid clash if used elsewhere
    CreateMessageResult,
    TextContent, # Re-used from request but part of response content
    CallToolResult,
    ContentBlock, # Union of content types
    TextResourceContents, # For embedded resource examples
    EmbeddedResource,
    MCPPartialResponse, # Still testing its structure
    create_jsonrpc_response,
    create_jsonrpc_error_response
)
from src.core.request import LATEST_PROTOCOL_VERSION # For InitializeResult

# General JSON-RPC Structures

def test_jsonrpc_response_creation():
    """Test creating a basic JSONRPCResponse."""
    req_id = "test-id-456"
    # Using InitializeResult as a concrete result type for testing
    server_impl = ServerImplementation(name="TestServer", version="0.2.0")
    server_caps = ServerCapabilities(logging={}, prompts={"listChanged": False})
    result_data = InitializeResult(
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=server_caps,
        serverInfo=server_impl,
        instructions="Welcome!"
    )

    jrpc_resp_direct = JSONRPCResponse(id=req_id, result=result_data)
    assert jrpc_resp_direct.jsonrpc == "2.0"
    assert jrpc_resp_direct.id == req_id
    assert isinstance(jrpc_resp_direct.result, InitializeResult)
    assert jrpc_resp_direct.result.instructions == "Welcome!"

    # Test with helper
    jrpc_resp_helper = create_jsonrpc_response(result_model=result_data, request_id=req_id)
    assert jrpc_resp_helper.jsonrpc == "2.0"
    assert jrpc_resp_helper.id == req_id
    assert jrpc_resp_helper.result == result_data


def test_jsonrpc_error_response_creation():
    """Test creating a JSONRPCErrorResponse."""
    req_id = "test-id-789"
    error_payload = {"code": -32600, "message": "Invalid Request"}

    jrpc_err_resp_direct = JSONRPCErrorResponse(id=req_id, error=error_payload)
    assert jrpc_err_resp_direct.jsonrpc == "2.0"
    assert jrpc_err_resp_direct.id == req_id
    assert jrpc_err_resp_direct.error["code"] == -32600

    # Test with helper
    jrpc_err_resp_helper = create_jsonrpc_error_response(
        code=-32601, message="Method not found", request_id=req_id, data={"method": "nonExistent"}
    )
    assert jrpc_err_resp_helper.jsonrpc == "2.0"
    assert jrpc_err_resp_helper.id == req_id
    assert jrpc_err_resp_helper.error["code"] == -32601
    assert jrpc_err_resp_helper.error["data"]["method"] == "nonExistent"


# Key MCP Result Models

def test_initialize_result():
    """Test InitializeResult model."""
    server_impl = ServerImplementation(name="AwesomeServer", version="1.0")
    caps = ServerCapabilities(tools={"listChanged": True}, resources={})
    result = InitializeResult(
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=caps,
        serverInfo=server_impl
    )
    assert result.serverInfo.name == "AwesomeServer"
    assert result.capabilities.tools["listChanged"] is True
    assert result.instructions is None # Optional field

    # Test serialization
    dumped = result.model_dump()
    assert dumped["serverInfo"]["name"] == "AwesomeServer"


def test_create_message_result():
    """Test CreateMessageResult model."""
    text_content = TextContent(text="Hello from assistant!")
    result = CreateMessageResult(
        role="assistant",
        content=text_content,
        model="claude-3-opus-20240229",
        stopReason="end_turn",
        _meta={"usage": {"input_tokens": 10, "output_tokens": 20}}
    )
    assert result.role == "assistant"
    assert isinstance(result.content, TextContent)
    assert result.content.text == "Hello from assistant!"
    assert result.model == "claude-3-opus-20240229"
    assert result._meta["usage"]["output_tokens"] == 20


def test_call_tool_result():
    """Test CallToolResult model."""
    # Example with simple text content
    text_res = TextContent(text="Tool execution successful: 2 + 2 = 4")
    result1 = CallToolResult(content=[text_res], isError=False)
    assert isinstance(result1.content[0], TextContent)
    assert "2 + 2 = 4" in result1.content[0].text
    assert result1.isError is False
    assert result1.structuredContent is None

    # Example with structured content and embedded resource
    json_data_str = '{"value": 4, "details": "Addition complete"}'
    embedded_res_content = EmbeddedResource(
        type="resource",
        resource=TextResourceContents(
            uri="tool://calculator/result/123",
            mimeType="application/json",
            text=json_data_str
        )
    )
    result2 = CallToolResult(
        content=[embedded_res_content],
        structuredContent={"value": 4, "details": "Addition complete"},
        isError=False
    )
    assert isinstance(result2.content[0], EmbeddedResource)
    assert isinstance(result2.content[0].resource, TextResourceContents)
    assert result2.content[0].resource.text == json_data_str
    assert result2.structuredContent["value"] == 4

    # Example of an error result from a tool
    error_text = TextContent(text="Tool Error: Division by zero")
    result_error = CallToolResult(content=[error_text], isError=True)
    assert result_error.isError is True


# MCPPartialResponse (retained from previous structure, for streaming)

def test_mcp_partial_response():
    """Test MCPPartialResponse model (used for streaming)."""
    partial1 = MCPPartialResponse(partial_text="Hello ")
    assert partial1.partial_text == "Hello "
    assert partial1.is_final_chunk is False
    assert partial1.data_chunk is None
    assert partial1.error is None

    partial_data = MCPPartialResponse(data_chunk={"type": "image_progress", "percent": 50}, metadata={"id": "img1"})
    assert partial_data.data_chunk["percent"] == 50
    assert partial_data.metadata["id"] == "img1"

    partial_final = MCPPartialResponse(is_final_chunk=True, metadata={"finish_reason": "stop"})
    assert partial_final.is_final_chunk is True
    assert partial_final.metadata["finish_reason"] == "stop"

    partial_error = MCPPartialResponse(error={"code": 123, "message": "Stream interrupted"}, is_final_chunk=True)
    assert partial_error.error["message"] == "Stream interrupted"
