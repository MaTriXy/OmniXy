"""Unit tests for MCP Request Pydantic models based on JSON-RPC."""

import pytest
from pydantic import ValidationError

from src.core.request import (
    JSONRPCRequest,
    JSONRPCNotification,
    InitializeRequest,
    InitializeRequestParams,
    ClientCapabilities,
    Implementation,
    LATEST_PROTOCOL_VERSION,
    CreateMessageRequest,
    CreateMessageRequestParams,
    SamplingMessage,
    TextContent,
    CallToolRequest,
    CallToolRequestParams,
    RequestMeta,
    create_jsonrpc_request,
    create_jsonrpc_notification,
    CancelledNotification,
    CancelledNotificationParams,
    ProgressNotification,
    ProgressNotificationParams
)

# General JSON-RPC Structures
def test_jsonrpc_request_creation():
    """Test creating a basic JSONRPCRequest."""
    req_id = "test-id-123"
    method = "example/method"
    params_data = InitializeRequestParams( # Using a concrete params type for test
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=ClientCapabilities(),
        clientInfo=Implementation(name="test-client", version="0.1.0")
    )

    jrpc_req_direct = JSONRPCRequest(id=req_id, method=method, params=params_data)
    assert jrpc_req_direct.jsonrpc == "2.0"
    assert jrpc_req_direct.id == req_id
    assert jrpc_req_direct.method == method
    assert isinstance(jrpc_req_direct.params, InitializeRequestParams)

    # Test with helper
    mcp_req_model = InitializeRequest(params=params_data) # method is set by model
    jrpc_req_helper = create_jsonrpc_request(request_model=mcp_req_model, request_id=req_id)
    assert jrpc_req_helper.jsonrpc == "2.0"
    assert jrpc_req_helper.id == req_id
    assert jrpc_req_helper.method == "initialize" # From InitializeRequest model
    assert jrpc_req_helper.params == params_data


def test_jsonrpc_notification_creation():
    """Test creating a basic JSONRPCNotification."""
    method = "example/notification"
    params_data = CancelledNotificationParams(requestId="req-to-cancel")

    jrpc_notif_direct = JSONRPCNotification(method=method, params=params_data)
    assert jrpc_notif_direct.jsonrpc == "2.0"
    assert jrpc_notif_direct.method == method
    assert jrpc_notif_direct.params == params_data

    # Test with helper
    mcp_notif_model = CancelledNotification(params=params_data)
    jrpc_notif_helper = create_jsonrpc_notification(notification_model=mcp_notif_model)
    assert jrpc_notif_helper.jsonrpc == "2.0"
    assert jrpc_notif_helper.method == "notifications/cancelled" # From model
    assert jrpc_notif_helper.params == params_data


def test_request_meta_progress_token():
    """Test RequestMeta with progressToken."""
    meta = RequestMeta(progressToken=123)
    params = InitializeRequestParams(
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=ClientCapabilities(),
        clientInfo=Implementation(name="test-client", version="0.1.0"),
        _meta=meta
    )
    assert params._meta.progressToken == 123

    # Test serialization includes _meta
    dumped = params.model_dump()
    assert dumped["_meta"]["progressToken"] == 123

# Key MCP Request Models

def test_initialize_request():
    """Test InitializeRequest model."""
    client_info = Implementation(name="TestClient", version="1.0.0", title="Test Client App")
    caps = ClientCapabilities(sampling={}, roots={"listChanged": True})
    params = InitializeRequestParams(
        protocolVersion=LATEST_PROTOCOL_VERSION,
        capabilities=caps,
        clientInfo=client_info
    )
    req = InitializeRequest(params=params)

    assert req.method == "initialize"
    assert req.params.protocolVersion == LATEST_PROTOCOL_VERSION
    assert req.params.clientInfo.name == "TestClient"
    assert req.params.capabilities.sampling == {}
    assert req.params.capabilities.roots["listChanged"] is True

    # Test serialization
    dumped = req.model_dump()
    assert dumped["method"] == "initialize"
    assert dumped["params"]["clientInfo"]["name"] == "TestClient"


def test_create_message_request():
    """Test CreateMessageRequest model."""
    text_content = TextContent(text="Hello, world!")
    msg = SamplingMessage(role="user", content=text_content)
    params = CreateMessageRequestParams(
        messages=[msg],
        maxTokens=100,
        temperature=0.7,
        # metadata could include provider-specific things like model name if not in higher level
        metadata={"openai_model_name": "gpt-4o"}
    )
    req = CreateMessageRequest(params=params)

    assert req.method == "sampling/createMessage"
    assert req.params.messages[0].role == "user"
    assert isinstance(req.params.messages[0].content, TextContent)
    assert req.params.messages[0].content.text == "Hello, world!"
    assert req.params.maxTokens == 100
    assert req.params.metadata["openai_model_name"] == "gpt-4o"

    # Test missing required fields (e.g. maxTokens)
    with pytest.raises(ValidationError):
        CreateMessageRequestParams(messages=[msg]) # maxTokens is required by schema


def test_call_tool_request():
    """Test CallToolRequest model."""
    params = CallToolRequestParams(
        name="calculator.add",
        arguments={"a": 1, "b": 2}
    )
    req = CallToolRequest(params=params)

    assert req.method == "tools/call"
    assert req.params.name == "calculator.add"
    assert req.params.arguments["a"] == 1

    # Test with no arguments
    params_no_args = CallToolRequestParams(name="utils.getTime")
    req_no_args = CallToolRequest(params=params_no_args)
    assert req_no_args.params.arguments is None


# Key MCP Notification Models
def test_cancelled_notification():
    """Test CancelledNotification model."""
    params = CancelledNotificationParams(requestId="req-abc", reason="User cancelled")
    notif = CancelledNotification(params=params)

    assert notif.method == "notifications/cancelled"
    assert notif.params.requestId == "req-abc"
    assert notif.params.reason == "User cancelled"


def test_progress_notification():
    """Test ProgressNotification model."""
    params = ProgressNotificationParams(
        progressToken="token-1",
        progress=50.0, # Ensure float is accepted
        total=100.0,
        message="Halfway there!"
    )
    notif = ProgressNotification(params=params)

    assert notif.method == "notifications/progress"
    assert notif.params.progressToken == "token-1"
    assert notif.params.progress == 50.0
    assert notif.params.total == 100.0

    params_no_total = ProgressNotificationParams(progressToken=1, progress=10)
    notif_no_total = ProgressNotification(params=params_no_total)
    assert notif_no_total.params.total is None
    assert isinstance(notif_no_total.params.progress, float) # Pydantic might convert int to float here
