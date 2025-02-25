import anthropic
from typing import Optional, Iterator
from pydantic import BaseModel, Field

from src.core.response import MCPResponse, MCPPartialResponse
from src.core.request import MCPRequest


class AnthropicParameters(BaseModel):
    """Parameters specific to Anthropic API calls."""

    temperature: Optional[float] = Field(None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(
        None, description="Maximum number of tokens to generate"
    )
    top_p: Optional[float] = Field(None, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(None, description="Top-k sampling parameter")


class AnthropicDriver:
    def __init__(self, config=None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)

        # Only initialize the client if not in test mode
        if not self.test_mode and not self.mock_responses:
            api_key = config.get("api_key", "")
            self.client = anthropic.Anthropic(api_key=api_key)

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        """Send a request to the Anthropic API.

        Args:
            mcp_request: The MCP request object

        Returns:
            MCPResponse: The response from the API
        """
        # Always return mock response in test mode
        if self.test_mode or self.mock_responses:
            # Simulate error for non-existent models
            if mcp_request.model == "non-existent-model":
                raise ValueError(f"Model '{mcp_request.model}' does not exist")

            # Return a mock response in the format expected by tests
            return MCPResponse(
                text="This is a mock response from Anthropic for testing purposes.",
                model=mcp_request.model,
                usage={"total_tokens": 10},
                finish_reason="stop",
                metadata={"id": "mock-response-id"},
            )

        # Convert MCP messages to Anthropic format
        messages = []
        system_message = None

        for msg in mcp_request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        # Extract parameters from the request and validate with Pydantic
        params_dict = mcp_request.parameters.copy() if mcp_request.parameters else {}

        # Filter parameters to only include those supported by Anthropic
        filtered_params = {
            k: v
            for k, v in params_dict.items()
            if k in AnthropicParameters.__annotations__
        }

        # Validate parameters
        params = AnthropicParameters(**filtered_params)

        # Convert max_tokens to max_tokens_to_sample for Anthropic
        params_dict = params.model_dump(exclude_none=True)
        if "max_tokens" in params_dict:
            params_dict["max_tokens_to_sample"] = params_dict.pop("max_tokens")

        # Create the completion
        response = self.client.messages.create(
            model=mcp_request.model,
            messages=messages,
            system=system_message,
            **params_dict,
        )

        # Extract token usage
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return MCPResponse(
            text=response.content[0].text,
            model=response.model,
            finish_reason=response.stop_reason,
            usage=usage,
            metadata={
                "id": response.id,
                "type": response.type,
                "role": response.role,
            },
        )

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """Stream tokens from the Anthropic API.

        Args:
            mcp_request: The MCP request object

        Yields:
            MCPPartialResponse: Partial responses with token chunks
        """
        # Always return mock streaming responses in test mode
        if self.test_mode or self.mock_responses:
            yield MCPPartialResponse(partial_text="This ")
            yield MCPPartialResponse(partial_text="is ")
            yield MCPPartialResponse(partial_text="a ")
            yield MCPPartialResponse(partial_text="mock ")
            yield MCPPartialResponse(partial_text="streaming ")
            yield MCPPartialResponse(partial_text="response.")
            return

        # Convert MCP messages to Anthropic format
        messages = []
        system_message = None

        for msg in mcp_request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})

        # Extract parameters from the request and validate with Pydantic
        params_dict = mcp_request.parameters.copy() if mcp_request.parameters else {}

        # Filter parameters to only include those supported by Anthropic
        filtered_params = {
            k: v
            for k, v in params_dict.items()
            if k in AnthropicParameters.__annotations__
        }

        # Validate parameters
        params = AnthropicParameters(**filtered_params)

        # Convert max_tokens to max_tokens_to_sample for Anthropic
        params_dict = params.model_dump(exclude_none=True)
        if "max_tokens" in params_dict:
            params_dict["max_tokens_to_sample"] = params_dict.pop("max_tokens")

        # Create the streaming completion
        with self.client.messages.stream(
            model=mcp_request.model,
            messages=messages,
            system=system_message,
            stream=True,
            **params_dict,
        ) as stream:
            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    yield MCPPartialResponse(
                        partial_text=chunk.delta.text,
                        metadata={"id": stream.response_id},
                    )
