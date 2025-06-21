"""Unit tests for the MCP layer, now focusing on JSON-RPC interactions."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.mcp_layer import MCPLayer, generate_request_id, INTERNAL_ERROR, INVALID_REQUEST
from src.core.request import (
    InitializeRequest, InitializeRequestParams, ClientCapabilities, Implementation,
    LATEST_PROTOCOL_VERSION,
    CreateMessageRequest, CreateMessageRequestParams, SamplingMessage, TextContent,
    ProgressNotification, ProgressNotificationParams, MCPNotification,
    JSONRPCRequest, # For verifying what MCPLayer constructs if it were to send externally
)
from src.core.response import (
    InitializeResult, ServerCapabilities, ServerImplementation,
    CreateMessageResult,
    JSONRPCResponse, JSONRPCErrorResponse, # Expected return types from MCPLayer.send_request
    MCPPartialResponse
)

@pytest.fixture
def mock_driver_manager():
    """Fixture for a MCPLayer with a mock driver manager (provider_drivers dict)."""
    mock_driver = AsyncMock() # Base mock for any driver

    # Mock for InitializeRequest -> InitializeResult
    async def mock_execute_initialize(req_model, req_id):
        if isinstance(req_model, InitializeRequest):
            return InitializeResult(
                protocolVersion=LATEST_PROTOCOL_VERSION,
                capabilities=ServerCapabilities(),
                serverInfo=ServerImplementation(name="mock-server", version="1.0")
            )
        raise TypeError(f"Mock execute_mcp_request cannot handle {type(req_model)}")

    # Mock for CreateMessageRequest -> CreateMessageResult
    async def mock_execute_create_message(req_model, req_id):
        if isinstance(req_model, CreateMessageRequest):
            # Simulate getting model name from metadata if that's the convention
            model_name = req_model.params.metadata.get("test_model_name", "default-mock-model")
            return CreateMessageResult(
                role="assistant",
                content=TextContent(text="Mocked LLM response"),
                model=model_name,
                stopReason="stop"
            )
        raise TypeError(f"Mock execute_mcp_request cannot handle {type(req_model)}")

    # Mock for streaming
    async def mock_stream_responses(req_model, req_id):
        if isinstance(req_model, CreateMessageRequest):
            yield MCPPartialResponse(partial_text="Stream part 1 ", metadata={"request_id": req_id})
            await asyncio.sleep(0) # Allow event loop to cycle
            yield MCPPartialResponse(partial_text="Stream part 2.", is_final_chunk=True, metadata={"request_id": req_id})
        else:
            yield MCPPartialResponse(error={"message": "Unsupported stream request"}, is_final_chunk=True)

    mock_driver.execute_mcp_request = AsyncMock() # Default mock
    mock_driver.stream_mcp_responses = MagicMock(return_value=mock_stream_responses(None, None)) # Needs to be an async generator
    mock_driver.handle_mcp_notification = AsyncMock()

    drivers = {
        "mock_general_provider": mock_driver, # For general tests
        "mock_init_provider": AsyncMock(execute_mcp_request=AsyncMock(side_effect=mock_execute_initialize)),
        "mock_llm_provider": AsyncMock(
            execute_mcp_request=AsyncMock(side_effect=mock_execute_create_message),
            stream_mcp_responses=MagicMock(side_effect=lambda req_model, req_id: mock_stream_responses(req_model, req_id)) # Ensure it's callable
        )
    }
    return MCPLayer(provider_drivers=drivers)


def test_mcp_layer_initialization(mock_driver_manager):
    """Test MCP layer initialization."""
    layer = mock_driver_manager # Using the fixture
    assert layer is not None
    assert hasattr(layer, "send_request")
    assert hasattr(layer, "send_notification")
    assert hasattr(layer, "stream_mcp_responses")


@pytest.mark.asyncio
async def test_mcp_layer_send_initialize_request(mock_driver_manager):
    """Test sending an InitializeRequest via MCPLayer."""
    layer = mock_driver_manager

    # Patch _get_driver_for_request to return the specific mock driver
    layer._get_driver_for_request = MagicMock(return_value=layer.provider_drivers["mock_init_provider"])

    init_params = InitializeRequestParams(
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=ClientCapabilities(),
        clientInfo=Implementation(name="test-client", version="0.1")
    )
    init_request_model = InitializeRequest(params=init_params)
    request_id = generate_request_id()

    response = await layer.send_request(init_request_model, request_id)

    assert isinstance(response, JSONRPCResponse)
    assert response.id == request_id
    assert isinstance(response.result, InitializeResult)
    assert response.result.serverInfo.name == "mock-server"

    # Verify the correct driver was called
    layer.provider_drivers["mock_init_provider"].execute_mcp_request.assert_awaited_once_with(init_request_model, request_id)


@pytest.mark.asyncio
async def test_mcp_layer_send_create_message_request(mock_driver_manager):
    """Test sending a CreateMessageRequest for LLM completion."""
    layer = mock_driver_manager
    layer._get_driver_for_request = MagicMock(return_value=layer.provider_drivers["mock_llm_provider"])

    cm_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(text="Hello"))],
        maxTokens=50,
        metadata={"test_model_name": "claude-mock-v1"} # Instruct mock which model to "use"
    )
    cm_request_model = CreateMessageRequest(params=cm_params)
    request_id = "cm-test-1"

    response = await layer.send_request(cm_request_model, request_id)

    assert isinstance(response, JSONRPCResponse)
    assert response.id == request_id
    assert isinstance(response.result, CreateMessageResult)
    assert response.result.role == "assistant"
    assert response.result.content.text == "Mocked LLM response"
    assert response.result.model == "claude-mock-v1"
    layer.provider_drivers["mock_llm_provider"].execute_mcp_request.assert_awaited_once_with(cm_request_model, request_id)


@pytest.mark.asyncio
async def test_mcp_layer_send_request_no_driver(mock_driver_manager):
    """Test error handling when no driver is found for a request."""
    layer = mock_driver_manager
    layer._get_driver_for_request = MagicMock(return_value=None) # Simulate no driver found

    init_params = InitializeRequestParams(protocolVersion="1.0", capabilities=ClientCapabilities(), clientInfo=Implementation(name="c",version="v"))
    init_request_model = InitializeRequest(params=init_params)
    request_id = "no-driver-test"

    response = await layer.send_request(init_request_model, request_id)

    assert isinstance(response, JSONRPCErrorResponse)
    assert response.id == request_id
    assert response.error["code"] == INTERNAL_ERROR
    assert "No driver found" in response.error["message"]


@pytest.mark.asyncio
async def test_mcp_layer_send_request_driver_exception(mock_driver_manager):
    """Test error handling when a driver raises an exception."""
    layer = mock_driver_manager

    # Configure the general mock driver to raise an exception
    mock_driver_instance = layer.provider_drivers["mock_general_provider"]
    mock_driver_instance.execute_mcp_request.side_effect = Exception("Driver internal error")
    layer._get_driver_for_request = MagicMock(return_value=mock_driver_instance)


    init_params = InitializeRequestParams(protocolVersion="1.0", capabilities=ClientCapabilities(), clientInfo=Implementation(name="c",version="v"))
    init_request_model = InitializeRequest(params=init_params)
    request_id = "driver-error-test"

    response = await layer.send_request(init_request_model, request_id)

    assert isinstance(response, JSONRPCErrorResponse)
    assert response.id == request_id
    assert response.error["code"] == INTERNAL_ERROR
    assert "Error processing request with driver: Driver internal error" in response.error["message"]


@pytest.mark.asyncio
async def test_mcp_layer_stream_mcp_responses(mock_driver_manager):
    """Test streaming responses via MCPLayer."""
    layer = mock_driver_manager
    layer._get_driver_for_request = MagicMock(return_value=layer.provider_drivers["mock_llm_provider"])

    cm_params = CreateMessageRequestParams(
        messages=[SamplingMessage(role="user", content=TextContent(text="Stream test"))],
        maxTokens=10
    )
    cm_request_model = CreateMessageRequest(params=cm_params)
    request_id = "stream-test-1"

    results = []
    async for partial_response in layer.stream_mcp_responses(cm_request_model, request_id):
        results.append(partial_response)

    assert len(results) == 2
    assert isinstance(results[0], MCPPartialResponse)
    assert results[0].partial_text == "Stream part 1 "
    assert results[0].is_final_chunk is False
    assert results[0].metadata["request_id"] == request_id

    assert isinstance(results[1], MCPPartialResponse)
    assert results[1].partial_text == "Stream part 2."
    assert results[1].is_final_chunk is True
    assert results[1].metadata["request_id"] == request_id

    layer.provider_drivers["mock_llm_provider"].stream_mcp_responses.assert_called_once_with(cm_request_model, request_id)

@pytest.mark.asyncio
async def test_mcp_layer_send_notification(mock_driver_manager):
    """Test sending a notification via MCPLayer."""
    layer = mock_driver_manager
    mock_general_driver = layer.provider_drivers["mock_general_provider"]
    layer._get_driver_for_request = MagicMock(return_value=mock_general_driver)

    prog_params = ProgressNotificationParams(progressToken="abc", progress=0.5, message="working")
    prog_notif_model = ProgressNotification(params=prog_params)

    await layer.send_notification(prog_notif_model)
    mock_general_driver.handle_mcp_notification.assert_awaited_once_with(prog_notif_model)

# Example of a removed/refactored test:
# The old `validate_request` and `format_response` are not directly applicable.
# Pydantic models handle their own validation.
# JSON-RPC wrapping is handled by `create_jsonrpc_request/response` or within `MCPConnection`.
# MCPLayer's role is now more about routing to drivers.

# def test_old_mcp_layer_protocol_validation_removed():
#     """Illustrate removal of old validation test."""
#     pass # This kind of direct validation by MCPLayer is changed.

# def test_old_mcp_layer_response_format_removed():
#     """Illustrate removal of old response formatting test."""
#     pass # Response formatting is now about creating specific Pydantic Result models.
