import json
import requests
from typing import Dict, List, Optional, Any, Iterator, Type, Union
from pydantic import BaseModel, Field, HttpUrl

from src.core.response import MCPResponse, MCPPartialResponse
from src.core.request import MCPRequest, Message


class ServerConfig(BaseModel):
    """Configuration for an MCP server connection."""

    url: str = Field(..., description="The server URL")
    protocol: str = Field("https", description="The protocol to use (http or https)")
    headers: Dict[str, str] = Field(
        default_factory=dict, description="Headers to include in requests"
    )
    timeout: int = Field(30, description="Request timeout in seconds")


class MCPLayer:
    """Layer for processing MCP requests and responses."""

    def __init__(self, provider_drivers: Optional[Dict[str, Any]] = None):
        """Initialize the MCP layer.

        Args:
            provider_drivers: Dictionary mapping provider names to driver instances
        """
        self.provider_drivers = provider_drivers or {}

    def process_request(self, request_data: Dict[str, Any]) -> MCPRequest:
        """Process an incoming request.

        Args:
            request_data: Raw request data

        Returns:
            MCPRequest: Processed request object
        """
        # Validate the request
        self.validate_request(request_data)

        # Convert to MCPRequest object
        return MCPRequest.from_dict(request_data)

    def validate_request(self, request_data: Dict[str, Any]) -> bool:
        """Validate a request against the MCP protocol.

        Args:
            request_data: Request data to validate

        Returns:
            bool: True if valid

        Raises:
            ValueError: If request is invalid
        """
        if not isinstance(request_data, dict):
            raise ValueError("Request must be a dictionary")

        if "messages" not in request_data:
            raise ValueError("Request must contain messages")

        if "model" not in request_data:
            raise ValueError("Request must specify a model")

        # Validate message format
        messages = request_data.get("messages", [])
        if not isinstance(messages, list) or len(messages) == 0:
            raise ValueError("Messages must be a non-empty list")

        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a dictionary")

            if "role" not in message or "content" not in message:
                raise ValueError("Each message must have role and content")

        return True

    def format_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a response according to the MCP protocol.

        Args:
            response_data: Raw response data

        Returns:
            dict: Formatted response
        """
        # Create a standardized response format
        formatted = {
            "text": response_data.get("text", ""),
            "usage": response_data.get("usage", {}),
            "model": response_data.get("model"),
            "finish_reason": response_data.get("finish_reason"),
            "metadata": response_data.get("metadata", {}),
        }

        return formatted

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        """Send a request to the appropriate provider.

        Args:
            mcp_request: The request to send

        Returns:
            MCPResponse: The response from the provider

        Raises:
            ValueError: If no driver is found for the provider
        """
        provider = mcp_request.provider
        if not provider and mcp_request.model:
            # Try to extract provider from model format like 'anthropic/claude-3.7-sonnet:beta'
            provider = (
                mcp_request.model.split("/")[0] if "/" in mcp_request.model else None
            )

        driver = self.provider_drivers.get(provider)
        if not driver:
            raise ValueError(f"No driver found for provider: {provider}")
        return driver.send_request(mcp_request)

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """Stream tokens from the appropriate provider.

        Args:
            mcp_request: The request to send

        Yields:
            MCPPartialResponse: Partial responses with token chunks

        Raises:
            ValueError: If no driver is found for the provider
        """
        provider = mcp_request.provider
        if not provider and mcp_request.model:
            # Try to extract provider from model format like 'anthropic/claude-3.7-sonnet:beta'
            provider = (
                mcp_request.model.split("/")[0] if "/" in mcp_request.model else None
            )

        driver = self.provider_drivers.get(provider)
        if not driver:
            raise ValueError(f"No driver found for provider: {provider}")
        return driver.stream_tokens(mcp_request)


class MCPConnection:
    """Connection to an MCP server."""

    def __init__(self, server_config: Union[Dict[str, Any], ServerConfig]):
        """Initialize the connection.

        Args:
            server_config: Configuration for the server connection
        """
        if isinstance(server_config, dict):
            self.config = ServerConfig(**server_config)
        else:
            self.config = server_config

    def send(self, mcp_request: MCPRequest) -> MCPResponse:
        """Send a request to the server.

        Args:
            mcp_request: The request to send

        Returns:
            MCPResponse: The response from the server
        """
        response = requests.post(
            f"{self.config.protocol}://{self.config.url}/complete",
            json=mcp_request.to_dict(),
            headers=self.config.headers,
            timeout=self.config.timeout,
        )
        return MCPResponse.from_dict(response.json())

    def stream(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """Stream a request to the server.

        Args:
            mcp_request: The request to send

        Yields:
            MCPPartialResponse: Partial responses with token chunks
        """
        with requests.post(
            f"{self.config.protocol}://{self.config.url}/stream",
            json=mcp_request.to_dict(),
            headers=self.config.headers,
            timeout=self.config.timeout,
            stream=True,
        ) as response:
            for chunk in response.iter_content(chunk_size=None):
                yield MCPPartialResponse.from_dict(json.loads(chunk))
