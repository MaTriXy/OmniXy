import json
import requests
import random
import string
import logging # Added for security/consent logging placeholders
from typing import Dict, Optional, Any, Iterator, Union, Type, TypeVar, Generic
from pydantic import BaseModel, Field, ValidationError

from src.core.response import (
    JSONRPCResponse,
    JSONRPCErrorResponse,
    MCPResponse,
    MCPPartialResponse, # Retained for potential streaming use, see note in response.py
    BaseResult,
    EmptyResult,
    create_jsonrpc_response,
    create_jsonrpc_error_response,
)
from src.core.request import (
    JSONRPCRequest,
    JSONRPCNotification,
    MCPRequest, # Union of ClientRequest and ServerRequest
    MCPNotification, # Union of ClientNotification and ServerNotification
    RequestId,
    ClientRequest,
    ServerRequest,
    CallToolRequest, # For specific check
    CreateMessageRequest, # For specific check
    ElicitRequest, # For specific check
    ReadResourceRequest, # For specific check
    create_jsonrpc_request,
    create_jsonrpc_notification,
)

# --- Logger Setup ---
logger = logging.getLogger(__name__)
# Basic configuration if no handlers are set by the application
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# --- End Logger Setup ---

# Define type variables for generic request and response handling
McpReq = TypeVar("McpReq", bound=Union[ClientRequest, ServerRequest, MCPNotification])
McpRes = TypeVar("McpRes", bound=BaseResult) # MCPResponse is a Union of BaseResults

INTERNAL_ERROR = -32603
INVALID_REQUEST = -32600
# More specific error codes can be defined as per JSON-RPC / MCP spec
USER_CONSENT_REQUIRED = -32000
OPERATION_CANCELLED_BY_USER = -32001

class ServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    url: str = Field(..., description="The server URL, e.g., 'localhost:8000/mcp'")
    protocol: str = Field("http", description="The protocol to use (http or https)")
    headers: Dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/json"},
        description="Headers to include in requests.",
    )
    timeout: int = Field(30, description="Request timeout in seconds")


def generate_request_id() -> RequestId:
    """Generates a unique request ID."""
    # Simple random string for now, consider UUIDs for more robustness
    return "".join(random.choices(string.ascii_letters + string.digits, k=10))


class MCPLayer:
    """
    Layer for processing MCP requests and responses based on JSON-RPC 2.0.
    This layer is responsible for interacting with provider drivers.
    It prepares JSON-RPC requests to send to drivers (if they are external MCP servers)
    or translates MCP standard requests to driver-specific formats.
    """

    def __init__(self, provider_drivers: Optional[Dict[str, Any]] = None):
        """
        Initialize the MCP layer.

        Args:
            provider_drivers: Dictionary mapping provider names to driver instances.
                              These drivers are responsible for actual communication
                              with LLMs or other services.
        """
        self.provider_drivers = provider_drivers or {}

    def _get_driver_for_request(self, mcp_request_params: Union[ClientRequest, ServerRequest]):
        """
        Determines the appropriate driver based on the MCP request.
        This is a placeholder and needs a robust mechanism.
        For example, it could be based on a field in the request,
        or a routing configuration.
        """
        # FIXME: This is a highly simplified way to get a provider.
        # In a real system, this would be more complex, potentially looking
        # at a 'provider' field in the top-level MCPRequest or specific fields
        # within the params of InitializeRequest, CallToolRequest etc.
        # For now, let's assume a 'default' driver or based on method.

        if hasattr(mcp_request_params, "params") and hasattr(mcp_request_params.params, "model"):
            # This is a very basic attempt to get a provider from a model string
            # e.g. "openai/gpt-4" -> "openai"
            model_str = getattr(mcp_request_params.params, "model", "")
            if isinstance(model_str, str) and "/" in model_str:
                provider_name = model_str.split("/")[0]
                if provider_name in self.provider_drivers:
                    return self.provider_drivers[provider_name]

        # Fallback or more sophisticated routing needed here
        # For now, if no specific provider, try a 'default' or first available.
        if "default" in self.provider_drivers:
            return self.provider_drivers["default"]
        if self.provider_drivers:
            return next(iter(self.provider_drivers.values()))
        return None


    async def send_request(
        self, mcp_request_model: McpReq, request_id: Optional[RequestId] = None
    ) -> Union[JSONRPCResponse, JSONRPCErrorResponse]:
        """
        Processes an MCP standard request (like InitializeRequest, CallToolRequest),
        wraps it in a JSONRPCRequest, and sends it to the appropriate provider driver.

        Args:
            mcp_request_model: The Pydantic model for the MCP request params (e.g., InitializeRequestParams).
            request_id: Optional request ID. If None, one will be generated.

        Returns:
            A JSONRPCResponse or JSONRPCErrorResponse.
        """
        if request_id is None:
            request_id = generate_request_id()

        # --- MCP Security & Trust Placeholder: User Consent ---
        # Before dispatching to a driver, especially for operations that involve
        # data access, tool execution, or LLM sampling, the application host
        # (integrating this MCPLayer) MUST ensure user consent has been obtained.
        # This is a placeholder logging call. A real implementation would involve
        # checking a consent status provided by the host application.
        if isinstance(mcp_request_model, (CallToolRequest, CreateMessageRequest, ReadResourceRequest)):
            logger.info(
                f"MCP_LAYER_SECURITY_CHECK: Processing {mcp_request_model.method} (ID: {request_id}). "
                "Host application MUST ensure explicit user consent was obtained for this action."
            )
        # If consent were not obtained, the MCPLayer should return an error:
        # return create_jsonrpc_error_response(
        #     code=USER_CONSENT_REQUIRED, # Example custom error code
        #     message="User consent required for this operation.",
        #     request_id=request_id
        # )
        # --- End MCP Security & Trust Placeholder ---

        driver = self._get_driver_for_request(mcp_request_model)
        if not driver:
            return create_jsonrpc_error_response(
                code=INTERNAL_ERROR,
                message=f"No driver found for request method: {mcp_request_model.method}",
                request_id=request_id,
            )

        # The driver's send_request method is now expected to handle an MCP Pydantic model
        # directly, rather than a pre-formed JSONRPCRequest object if it's an internal driver.
        # If the driver itself is an MCP server, it would expect a JSONRPCRequest.
        # This part needs clarification based on driver architecture.
        # Assuming drivers have a method like `execute_mcp_request`.
        try:
            # Let's assume drivers have a method `execute_mcp_request`
            # that takes the MCP Pydantic model (e.g. CallToolRequest) and returns
            # the corresponding MCP Result model (e.g. CallToolResult).
            if not hasattr(driver, "execute_mcp_request"):
                raise NotImplementedError(f"Driver for {driver.__class__.__name__} does not implement 'execute_mcp_request'")

            mcp_result: BaseResult = await driver.execute_mcp_request(mcp_request_model, request_id)
            return create_jsonrpc_response(result_model=mcp_result, request_id=request_id)

        except ValidationError as e:
            return create_jsonrpc_error_response(
                code=INVALID_REQUEST, # Or a more specific error
                message=f"Request validation error for driver: {str(e)}",
                request_id=request_id,
                data=e.errors()
            )
        except Exception as e:
            # Log the full error for debugging
            print(f"Error during driver execution: {e}")
            return create_jsonrpc_error_response(
                code=INTERNAL_ERROR,
                message=f"Error processing request with driver: {str(e)}",
                request_id=request_id,
            )

    async def send_notification(self, mcp_notification_model: MCPNotification) -> None:
        """
        Processes an MCP standard notification and sends it to the appropriate provider driver.
        This might be less common if MCPLayer is primarily a client, but included for completeness.
        """
        driver = self._get_driver_for_request(mcp_notification_model) # May need refinement for notifications
        if not driver:
            print(f"Warning: No driver found for notification method: {mcp_notification_model.method}")
            return

        try:
            if not hasattr(driver, "handle_mcp_notification"):
                print(f"Warning: Driver {driver.__class__.__name__} does not implement 'handle_mcp_notification'")
                return
            await driver.handle_mcp_notification(mcp_notification_model)
        except Exception as e:
            print(f"Error processing notification with driver: {str(e)}")


    # stream_tokens needs significant redesign for JSON-RPC.
    # JSON-RPC doesn't natively support streaming responses for a single request.
    # Streaming is typically handled via:
    # 1. Server-Sent Events (SSE) on a separate endpoint.
    # 2. WebSockets, where multiple messages can be sent over a persistent connection.
    # 3. MCP's `notifications/progress` where each notification carries a chunk.
    # For now, this method will be adapted to yield MCPPartialResponse,
    # assuming the driver can provide such an iterator and the caller handles it.
    # The MCPConnection layer would then need to wrap these into notifications if sending over JSON-RPC.
    async def stream_mcp_responses(
        self, mcp_request_model: McpReq, request_id: Optional[RequestId] = None
    ) -> Iterator[MCPPartialResponse]: # Or Iterator[ProgressNotification]
        """
        Initiates a request that is expected to stream responses.
        The underlying driver should provide an iterator of partial responses.
        """
        if request_id is None:
            request_id = generate_request_id() # Important for correlating progress notifications

        # --- MCP Security & Trust Placeholder: User Consent for Streaming ---
        # Similar to send_request, consent is crucial before initiating streams
        # that might involve sensitive operations or data.
        if isinstance(mcp_request_model, (CreateMessageRequest)): # Typically CreateMessageRequest for LLM streaming
            logger.info(
                f"MCP_LAYER_SECURITY_CHECK: Initiating stream for {mcp_request_model.method} (ID: {request_id}). "
                "Host application MUST ensure explicit user consent was obtained."
            )
        # If consent were not obtained:
        # yield MCPPartialResponse(
        #     error={"code": USER_CONSENT_REQUIRED, "message": "User consent required for this streaming operation."},
        #     is_final_chunk=True
        # )
        # return
        # --- End MCP Security & Trust Placeholder ---

        driver = self._get_driver_for_request(mcp_request_model)
        if not driver:
            # Yield a single error response if no driver
            yield MCPPartialResponse(
                error={"code": INTERNAL_ERROR, "message": f"No driver found for request: {mcp_request_model.method}"},
                is_final_chunk=True
            )
            return

        try:
            if not hasattr(driver, "stream_mcp_responses"):
                 raise NotImplementedError(f"Driver for {driver.__class__.__name__} does not implement 'stream_mcp_responses'")

            async for partial_response in driver.stream_mcp_responses(mcp_request_model, request_id):
                yield partial_response
        except Exception as e:
            yield MCPPartialResponse(
                error={"code": INTERNAL_ERROR, "message": f"Error streaming from driver: {str(e)}"},
                is_final_chunk=True
            )


class MCPConnection(Generic[McpReq, McpRes]):
    """
    Connection to an MCP server using JSON-RPC over HTTP.
    This class is responsible for the actual HTTP communication.
    """

    def __init__(self, server_config: Union[Dict[str, Any], ServerConfig]):
        if isinstance(server_config, dict):
            self.config = ServerConfig(**server_config)
        else:
            self.config = server_config
        self._session = requests.Session()
        self._session.headers.update(self.config.headers)

    async def send(
        self,
        mcp_request_model: McpReq,
        response_type: Type[McpRes], # Expected MCP Result type (e.g. InitializeResult)
        request_id: Optional[RequestId] = None
    ) -> Union[McpRes, JSONRPCErrorResponse]:
        """
        Sends an MCP request (e.g., InitializeRequest) to the server
        and expects a specific MCP Result type (e.g., InitializeResult).

        Args:
            mcp_request_model: The Pydantic model for the MCP request (e.g., InitializeRequest).
            response_type: The Pydantic model of the expected MCP Result (e.g., InitializeResult).
            request_id: Optional request ID.

        Returns:
            The parsed MCP Result Pydantic model on success, or JSONRPCErrorResponse on error.
        """
        if request_id is None:
            request_id = generate_request_id()

        # --- MCP Security & Trust Placeholder: User Consent & Data Privacy (Client-side) ---
        # When MCPConnection is used to send requests TO an external MCP Server:
        # - For `tools/call`: The user MUST consent before this client application invokes a tool on the external server.
        # - For `resources/read` or any request that might send local data: User consent is paramount.
        # - For `sampling/createMessage` (if this client were acting as a server, responding to such a request):
        #   User consent for using a local LLM and sharing results back.
        # This placeholder logs the intent. The calling application is responsible for actual consent mechanisms.
        log_sec_message = None
        if isinstance(mcp_request_model, CallToolRequest):
            log_sec_message = f"Calling external tool '{mcp_request_model.params.name}'."
        elif isinstance(mcp_request_model, ReadResourceRequest):
            log_sec_message = f"Requesting to read external resource '{mcp_request_model.params.uri}'."
        # Add more checks for other sensitive operations if this client can initiate them.

        if log_sec_message:
            logger.info(
                f"MCP_CONNECTION_SECURITY_CHECK: {log_sec_message} (Req ID: {request_id}). "
                "Application MUST ensure user consent before sending this request to an external MCP server."
            )
        # If consent were not obtained, the application should not call `MCPConnection.send()`
        # or should handle the error appropriately if this layer were to enforce it.
        # Example:
        # if not consent_given_for_external_tool_call(mcp_request_model.params.name):
        #     return JSONRPCErrorResponse(...)
        # --- End MCP Security & Trust Placeholder ---

        json_rpc_payload = create_jsonrpc_request(
            request_model=mcp_request_model, request_id=request_id
        ).model_dump(exclude_none=True)

        try:
            # Actual HTTP request sending
            logger.debug(f"MCPConnection: Sending request (ID: {request_id}, Method: {mcp_request_model.method}) to {self.config.url}")
            http_response = self._session.post(
                f"{self.config.protocol}://{self.config.url}",
                json=json_rpc_payload,
                timeout=self.config.timeout,
            )
            http_response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            response_data = http_response.json()

            if "error" in response_data:
                # TODO: Parse into a structured JSONRPCErrorResponse.error model
                return JSONRPCErrorResponse(**response_data)
            if "result" in response_data:
                # Ensure the result is parsed into the specific McpRes type
                # The `result` field itself is the McpRes model
                parsed_result = response_type.model_validate(response_data["result"])
                return parsed_result # This is the McpRes (e.g. InitializeResult)
            else:
                return JSONRPCErrorResponse(
                    id=request_id,
                    error={
                        "code": INTERNAL_ERROR,
                        "message": "Invalid JSON-RPC response: missing 'result' or 'error'",
                    }
                )
        except requests.exceptions.RequestException as e:
            return JSONRPCErrorResponse(
                id=request_id, error={"code": INTERNAL_ERROR, "message": f"HTTP request failed: {str(e)}"}
            )
        except json.JSONDecodeError:
            return JSONRPCErrorResponse(
                id=request_id, error={"code": INTERNAL_ERROR, "message": "Failed to decode JSON response"}
            )
        except ValidationError as e:
             return JSONRPCErrorResponse(
                id=request_id, error={"code": INTERNAL_ERROR, "message": f"Response validation error: {str(e)}", "data": e.errors()}
            )


    async def notify(self, mcp_notification_model: MCPNotification) -> bool:
        """
        Sends an MCP notification (e.g., InitializedNotification) to the server.
        Returns True on success (HTTP 2xx), False otherwise.
        """
        json_rpc_payload = create_jsonrpc_notification(
            notification_model=mcp_notification_model
        ).model_dump(exclude_none=True)

        try:
            http_response = self._session.post(
                f"{self.config.protocol}://{self.config.url}",
                json=json_rpc_payload,
                timeout=self.config.timeout,
            )
            http_response.raise_for_status()
            # For notifications, a 204 No Content or 202 Accepted is also fine.
            # raise_for_status() covers 200-299.
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to send notification: {str(e)}")
            return False

    # Streaming via simple HTTP POST that returns a stream is not standard JSON-RPC.
    # If the server supports streaming via a mechanism like Server-Sent Events (SSE)
    # or if it sends multiple JSON objects over a single HTTP response (problematic),
    # this method would need to be adapted.
    #
    # For MCP, streaming updates are often done via `notifications/progress`.
    # So, a `stream` method here might subscribe to such notifications or connect
    # to a WebSocket endpoint if the server provides one.
    #
    # The current `MCPPartialResponse` is kept from the old structure.
    # If we assume the server sends a stream of JSON objects (one per line, for example),
    # then this could parse them.
    async def stream_responses(
        self,
        mcp_request_model: McpReq, # The initial request to start the stream
        request_id: Optional[RequestId] = None
    ) -> Iterator[MCPPartialResponse]: # Or Iterator[ProgressNotificationParams]
        """
        Sends an initial request and then expects a stream of responses.
        This is a conceptual placeholder. True JSON-RPC streaming is complex.
        It might involve listening for `notifications/progress`.
        This example assumes the server provides a non-standard HTTP stream of JSON objects.
        """
        if request_id is None:
            request_id = generate_request_id()

        json_rpc_payload = create_jsonrpc_request(
            request_model=mcp_request_model, request_id=request_id
        ).model_dump(exclude_none=True)

        # This is where it gets non-standard for JSON-RPC over plain HTTP.
        # A server might use a different endpoint for streaming or expect a header.
        # For this example, let's assume the server returns a stream of JSON lines.
        try:
            with self._session.post(
                f"{self.config.protocol}://{self.config.url}", # May need a dedicated stream endpoint
                json=json_rpc_payload,
                timeout=self.config.timeout,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            # Each line is expected to be a JSON object representing
                            # a part of the stream, perhaps a ProgressNotification's params
                            # or an MCPPartialResponse-like structure.
                            chunk_data = json.loads(line.decode('utf-8'))
                            # Here, we assume the chunk_data can be parsed into MCPPartialResponse
                            # or a ProgressNotification's params.
                            # This needs to align with what the server actually sends.
                            # For simplicity, let's assume it's MCPPartialResponse for now.
                            yield MCPPartialResponse.model_validate(chunk_data)
                        except json.JSONDecodeError:
                            yield MCPPartialResponse(error={"message": "Failed to decode stream chunk"}, is_final_chunk=False)
                        except ValidationError as e:
                            yield MCPPartialResponse(error={"message": f"Stream chunk validation error: {e.errors()}"}, is_final_chunk=False)
        except requests.exceptions.RequestException as e:
            yield MCPPartialResponse(error={"message": f"Stream request failed: {str(e)}"}, is_final_chunk=True)
        except Exception as e: # Catch any other unexpected errors
            yield MCPPartialResponse(error={"message": f"Unexpected error during streaming: {str(e)}"}, is_final_chunk=True)

    def close(self):
        self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
