import openai
import asyncio
from typing import Optional, AsyncIterator, Dict, Any, Union
from pydantic import BaseModel, Field

from src.core.response import MCPPartialResponse, CreateMessageResult, BaseResult, CallToolResult # Assuming CallToolResult for other tools
from src.core.request import (
    MCPRequest, # This is now a Union of specific request types
    CreateMessageRequest,
    CallToolRequest, # Example for a generic tool call
    RequestId,
    SamplingMessage as MCPSamplingMessage, # Renamed to avoid conflict
    TextContent as MCPTextContent,
    # Add other MCP request types this driver might handle, e.g. CallToolRequest
)


# OpenAI specific parameter validation (can be part of CreateMessageRequest.params.metadata or similar)
class OpenAIChatParameters(BaseModel):
    temperature: Optional[float] = Field(None)
    max_tokens: Optional[int] = Field(None)
    top_p: Optional[float] = Field(None)
    frequency_penalty: Optional[float] = Field(None)
    presence_penalty: Optional[float] = Field(None)
    # stop: Optional[Union[str, list[str]]] = None # Not directly in CreateMessageRequest, could be metadata


class OpenAIDriver:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)
        self.api_key = config.get("api_key")

        # Initialize the client using the async version
        if not self.test_mode and not self.mock_responses:
            if not self.api_key:
                raise ValueError("OpenAI API key is required when not in test/mock mode.")
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        else:
            # Provide a mock client or None for test/mock modes
            self.client = None


    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        """
        Execute an MCP request using the OpenAI API.
        This driver primarily handles `CreateMessageRequest` for chat completions.
        """
        if isinstance(mcp_request_model, CreateMessageRequest):
            return await self._handle_create_message(mcp_request_model, request_id)
        # Add handlers for other MCPRequest types if this driver supports them
        # elif isinstance(mcp_request_model, CallToolRequest):
        #     # Example: return await self._handle_openai_tool_call(mcp_request_model, request_id)
        #     raise NotImplementedError(f"OpenAIDriver does not yet support {type(mcp_request_model).__name__}")
        else:
            # This error should ideally be an MCPErrorResult or similar
            raise NotImplementedError(
                f"OpenAIDriver does not support request type: {type(mcp_request_model).__name__}"
            )

    def _prepare_openai_messages(self, mcp_messages: list[MCPSamplingMessage]) -> list[Dict[str, Any]]:
        oai_messages = []
        for msg in mcp_messages:
            if isinstance(msg.content, MCPTextContent):
                oai_messages.append({"role": msg.role, "content": msg.content.text})
            # TODO: Handle ImageContent, AudioContent if supported by this driver path
            else:
                # For now, skip non-text content or raise error
                print(f"Warning: Skipping non-text content in message for OpenAI: {type(msg.content)}")
        return oai_messages

    async def _handle_create_message(
        self, request_params: CreateMessageRequest.params, request_id: RequestId
    ) -> CreateMessageResult:
        """Handles MCP CreateMessageRequest for OpenAI."""

        # Extract model from metadata or a conventional field if we adapt CreateMessageRequest
        # For now, let's assume model is passed via a specific way or default.
        # This is a simplification; model selection needs a robust strategy.
        # Let's assume `request_params.metadata` might contain `openai_model_name`
        openai_model_name = request_params.metadata.get("openai_model_name", "gpt-3.5-turbo") # Default if not specified

        if self.test_mode or self.mock_responses:
            if openai_model_name == "non-existent-model":
                # This should be an MCP Error structure, not raising Python error directly to MCPLayer
                # For now, this matches old behavior, but ideally MCPLayer gets a structured error
                raise ValueError(f"Model '{openai_model_name}' does not exist in mock mode")

            mock_content = MCPTextContent(text="This is a mock response from OpenAI for testing.")
            return CreateMessageResult(
                role="assistant",
                content=mock_content,
                model=openai_model_name, # Echo back the model used
                stopReason="stop",
                _meta={"usage": {"total_tokens": 10}, "id": f"mock-resp-{request_id}"}
            )

        oai_messages = self._prepare_openai_messages(request_params.messages)
        if not oai_messages:
            raise ValueError("No valid text messages found for OpenAI request.")


        # Prepare OpenAI specific parameters
        # Parameters from CreateMessageRequest take precedence, then from metadata
        openai_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
            # top_p, frequency_penalty, presence_penalty could be in request_params.metadata
        }
        if request_params.metadata:
            metadata_params = request_params.metadata.get("openai_params", {})
            if isinstance(metadata_params, dict):
                # Validate these params if needed
                openai_params.update({k: v for k, v in metadata_params.items() if v is not None})


        # Validate with Pydantic model if desired, or pass directly
        try:
            validated_openai_params = OpenAIChatParameters(**{k: v for k, v in openai_params.items() if v is not None})
        except Exception as e: # Pydantic ValidationError
            # Handle validation error appropriately, maybe return an error result
            raise ValueError(f"Invalid OpenAI parameters: {e}")


        response = await self.client.chat.completions.create(
            model=openai_model_name,
            messages=oai_messages,
            **validated_openai_params.model_dump(exclude_none=True),
        )

        response_choice = response.choices[0]
        response_message = response_choice.message

        # Construct MCPTextContent for the response
        # Assuming OpenAI returns text content here.
        # If it could return multimodal, this needs adjustment.
        response_text_content = MCPTextContent(text=response_message.content or "")

        return CreateMessageResult(
            role="assistant", # OpenAI's response role is typically 'assistant'
            content=response_text_content,
            model=response.model, # Actual model string from OpenAI response
            stopReason=response_choice.finish_reason,
            _meta={
                "id": response.id,
                "created": response.created,
                "usage": response.usage.model_dump() if response.usage else None,
                # Add any other relevant metadata from OpenAI response
            }
        )

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        """Stream responses for an MCP request, typically CreateMessageRequest."""

        if not isinstance(mcp_request_model, CreateMessageRequest):
            yield MCPPartialResponse(
                error={"code": -32600, "message": f"Streaming not supported for {type(mcp_request_model).__name__}"},
                is_final_chunk=True
            )
            return

        request_params = mcp_request_model.params
        openai_model_name = request_params.metadata.get("openai_model_name", "gpt-3.5-turbo")


        if self.test_mode or self.mock_responses:
            mock_stream_parts = ["This ", "is ", "a ", "mock ", "streaming ", "response."]
            for i, part in enumerate(mock_stream_parts):
                await asyncio.sleep(0.01) # Simulate network latency
                yield MCPPartialResponse(
                    partial_text=part,
                    is_final_chunk=(i == len(mock_stream_parts) - 1),
                    metadata={"request_id": request_id}
                )
            return

        oai_messages = self._prepare_openai_messages(request_params.messages)
        if not oai_messages:
            yield MCPPartialResponse(
                error={"code": -32600, "message": "No valid text messages for OpenAI stream."},
                is_final_chunk=True
            )
            return

        openai_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
        }
        if request_params.metadata:
            metadata_params = request_params.metadata.get("openai_params", {})
            if isinstance(metadata_params, dict):
                 openai_params.update({k: v for k, v in metadata_params.items() if v is not None})

        try:
            validated_openai_params = OpenAIChatParameters(**{k: v for k, v in openai_params.items() if v is not None})
        except Exception as e: # Pydantic ValidationError
            yield MCPPartialResponse(
                error={"code": -32602, "message": f"Invalid OpenAI parameters for stream: {e}"},
                is_final_chunk=True
            )
            return

        stream = await self.client.chat.completions.create(
            model=openai_model_name,
            messages=oai_messages,
            stream=True,
            **validated_openai_params.model_dump(exclude_none=True),
        )

        async for chunk in stream:
            delta_content = chunk.choices[0].delta.content
            if delta_content is not None:
                yield MCPPartialResponse(
                    partial_text=delta_content,
                    metadata={"id": chunk.id, "model": chunk.model, "request_id": request_id}, # Include request_id for correlation
                    is_final_chunk=False, # This will be true on the *last* yield after loop if needed
                )

        # After the loop, signify the end of the stream if the API doesn't do it explicitly per chunk
        # OpenAI's stream typically ends when the iteration finishes.
        # The `is_final_chunk` in MCPPartialResponse is tricky here.
        # One option is to send one last MCPPartialResponse with is_final_chunk=True and no text.
        # Or, the receiver of this async iterator detects completion when the iterator is exhausted.
        # For now, let's assume the caller handles exhaustion as "final".
        # If an explicit final chunk is needed:
        # yield MCPPartialResponse(is_final_chunk=True, metadata={"request_id": request_id})

    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        """
        Handle an MCP notification. OpenAI driver typically doesn't act on notifications from client.
        Placeholder for future use if needed.
        """
        # print(f"OpenAIDriver received notification: {mcp_notification_model.method}")
        pass # OpenAI driver usually initiates, doesn't receive notifications to act on
