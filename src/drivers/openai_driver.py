import openai
from typing import Optional, Iterator
from pydantic import BaseModel, Field

from src.core.response import MCPResponse, MCPPartialResponse
from src.core.request import MCPRequest


class OpenAIParameters(BaseModel):
    """Parameters specific to OpenAI API calls."""

    temperature: Optional[float] = Field(None, description="Sampling temperature")
    max_tokens: Optional[int] = Field(
        None, description="Maximum number of tokens to generate"
    )
    top_p: Optional[float] = Field(None, description="Nucleus sampling parameter")
    frequency_penalty: Optional[float] = Field(
        None, description="Frequency penalty parameter"
    )
    presence_penalty: Optional[float] = Field(
        None, description="Presence penalty parameter"
    )


class OpenAIDriver:
    def __init__(self, config=None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)

        # Only initialize the client if not in test mode
        if not self.test_mode and not self.mock_responses:
            api_key = config.get("api_key", "")
            self.client = openai.OpenAI(api_key=api_key)

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        """Send a request to the OpenAI API.

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
                text="This is a mock response from OpenAI for testing purposes.",
                model=mcp_request.model,
                usage={"total_tokens": 10},
                finish_reason="stop",
                metadata={"id": "mock-response-id"},
                is_chunk=False
            )

        # Only make API calls if not in test mode
        messages = [
            {"role": msg.role, "content": msg.content} for msg in mcp_request.messages
        ]

        # Extract parameters from the request and validate with Pydantic
        params_dict = mcp_request.parameters.copy() if mcp_request.parameters else {}

        # Filter parameters to only include those supported by OpenAI
        filtered_params = {
            k: v
            for k, v in params_dict.items()
            if k in OpenAIParameters.__annotations__
        }

        # Validate parameters
        params = OpenAIParameters(**filtered_params)

        response = self.client.chat.completions.create(
            model=mcp_request.model,
            messages=messages,
            **params.model_dump(exclude_none=True),
        )

        return MCPResponse(
            text=response.choices[0].message.content,
            model=response.model,
            finish_reason=response.choices[0].finish_reason,
            usage={"total_tokens": response.usage.total_tokens},
            metadata={
                "id": response.id,
                "created": response.created,
            },
            is_chunk=False
        )

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """Stream tokens from the OpenAI API.

        Args:
            mcp_request: The MCP request object

        Yields:
            MCPPartialResponse: Partial responses with token chunks
        """
        # Always return mock streaming responses in test mode
        if self.test_mode or self.mock_responses:
            yield MCPPartialResponse(partial_text="This ", is_final=False)
            yield MCPPartialResponse(partial_text="is ", is_final=False)
            yield MCPPartialResponse(partial_text="a ", is_final=False)
            yield MCPPartialResponse(partial_text="mock ", is_final=False)
            yield MCPPartialResponse(partial_text="streaming ", is_final=False)
            yield MCPPartialResponse(partial_text="response.", is_final=True)
            return

        # Extract parameters from the request and validate with Pydantic
        params_dict = mcp_request.parameters.copy() if mcp_request.parameters else {}

        # Filter parameters to only include those supported by OpenAI
        filtered_params = {
            k: v
            for k, v in params_dict.items()
            if k in OpenAIParameters.__annotations__
        }

        # Validate parameters
        params = OpenAIParameters(**filtered_params)

        # Only make API calls if not in test mode
        messages = [
            {"role": msg.role, "content": msg.content} for msg in mcp_request.messages
        ]

        response = self.client.chat.completions.create(
            model=mcp_request.model,
            messages=messages,
            stream=True,
            **params.model_dump(exclude_none=True),
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield MCPPartialResponse(
                    partial_text=chunk.choices[0].delta.content,
                    metadata={"id": chunk.id},
                    is_final=False
                )
