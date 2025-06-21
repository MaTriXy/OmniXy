from anthropic import AsyncAnthropic # Use AsyncAnthropic
import asyncio
import logging
from typing import Optional, AsyncIterator, Dict, Any, List
from pydantic import BaseModel, Field

from src.core.response import MCPPartialResponse, CreateMessageResult, BaseResult
from src.core.request import (
    MCPRequest,
    CreateMessageRequest,
    RequestId,
    SamplingMessage as MCPSamplingMessage,
    TextContent as MCPTextContent,
    ImageContent as MCPImageContent,
)

logger = logging.getLogger(__name__)

# Anthropic specific parameter validation
class AnthropicChatParameters(BaseModel):
    temperature: Optional[float] = Field(None)
    max_tokens: Optional[int] = Field(None)
    top_p: Optional[float] = Field(None)
    top_k: Optional[int] = Field(None)
    stop_sequences: Optional[List[str]] = Field(None)


class AnthropicDriver:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.test_mode = config.get("test_mode", False) 
        self.mock_responses = config.get("mock_responses", False)
        self.api_key = config.get("api_key")

        if not self.test_mode and not self.mock_responses:
            if not self.api_key:
                raise ValueError("Anthropic API key is required when not in test/mock mode.")
            # Ensure AsyncAnthropic is used
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            self.client = None # No client needed for mock/test

    def _mcp_to_anthropic_messages(self, mcp_messages: List[MCPSamplingMessage]) -> List[Dict[str, Any]]:
        anthropic_messages = []
        for msg in mcp_messages:
            if msg.role == "system": # System prompts are handled by a top-level parameter
                continue

            role = "user" if msg.role == "user" else "assistant"

            content_parts = []
            if isinstance(msg.content, MCPTextContent):
                content_parts.append({"type": "text", "text": msg.content.text})
            elif isinstance(msg.content, MCPImageContent):
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64", # Anthropic expects base64 string for image data
                        "media_type": msg.content.mimeType,
                        "data": msg.content.data,
                    }
                })
            else:
                logger.warning(f"AnthropicDriver skipping unsupported MCP content type: {type(msg.content)}")
                continue

            if content_parts:
                anthropic_messages.append({"role": role, "content": content_parts})
        return anthropic_messages

    def _get_system_prompt(self, mcp_messages: List[MCPSamplingMessage]) -> Optional[str]:
        system_prompts = [
            msg.content.text for msg in mcp_messages
            if msg.role == "system" and isinstance(msg.content, MCPTextContent)
        ]
        return "\n".join(system_prompts) if system_prompts else None

    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        if isinstance(mcp_request_model, CreateMessageRequest):
            return await self._handle_create_message(mcp_request_model, request_id)
        else:
            logger.error(f"AnthropicDriver received unsupported request type: {type(mcp_request_model).__name__}")
            raise NotImplementedError(
                f"AnthropicDriver does not support request type: {type(mcp_request_model).__name__}"
            )

    async def _handle_create_message(
        self, request_container: CreateMessageRequest, request_id: RequestId
    ) -> CreateMessageResult:
        request_params = request_container.params
        # Default to a known recent model if not specified, ensure it's a valid Anthropic model ID
        anthropic_model_name = request_params.metadata.get("anthropic_model_name", "claude-3-haiku-20240307")

        if self.test_mode or self.mock_responses:
            logger.info(f"AnthropicDriver running in test/mock mode for request_id: {request_id}")
            if anthropic_model_name == "non-existent-model":
                 raise ValueError(f"Model '{anthropic_model_name}' does not exist in mock mode")

            mock_text_content = MCPTextContent(text="This is a mock response from Anthropic for testing purposes.")
            return CreateMessageResult(
                role="assistant",
                content=mock_text_content,
                model=anthropic_model_name,
                stopReason="end_turn",
                _meta={
                    "id": f"mock-anthropic-resp-{request_id}",
                    "usage": {"input_tokens": 5, "output_tokens": 5}
                }
            )

        anthropic_messages = self._mcp_to_anthropic_messages(request_params.messages)
        system_prompt = self._get_system_prompt(request_params.messages)

        if not anthropic_messages:
             logger.warning(f"Anthropic request {request_id} requires at least one user or assistant message.")
             return CreateMessageResult(role="assistant", content=MCPTextContent(text="Error: No valid user/assistant messages for Anthropic request."), model=anthropic_model_name, stopReason="ERROR")

        api_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
        }
        if request_params.metadata and "anthropic_params" in request_params.metadata:
            extra_params = request_params.metadata["anthropic_params"]
            if isinstance(extra_params, dict):
                try:
                    valid_extra_params = AnthropicChatParameters(**extra_params).model_dump(exclude_none=True)
                    api_params.update(valid_extra_params)
                except Exception as e: # Pydantic validation error
                    logger.warning(f"Invalid Anthropic parameters in metadata for {request_id}: {e}")

        api_params = {k: v for k, v in api_params.items() if v is not None}
        # Anthropic's messages API requires max_tokens.
        if "max_tokens" not in api_params or api_params["max_tokens"] is None:
            api_params["max_tokens"] = 1024 # Default if not provided or None

        try:
            logger.debug(f"Sending to Anthropic (req_id: {request_id}): model={anthropic_model_name}, messages_count={len(anthropic_messages)}, system_present={bool(system_prompt)}, params={api_params}")
            response = await self.client.messages.create(
                model=anthropic_model_name,
                messages=anthropic_messages,
                system=system_prompt if system_prompt else None, # Pass None if no system prompt
                **api_params,
            )
        except Exception as e:
            logger.error(f"Anthropic API Error for request_id {request_id}: {e}", exc_info=True)
            error_text = f"Error from Anthropic: {type(e).__name__} - {str(e)}"
            return CreateMessageResult(
                role="assistant", content=MCPTextContent(text=error_text), model=anthropic_model_name,
                stopReason="ERROR", _meta={"id": f"error-anthropic-resp-{request_id}", "error_details": str(e)}
            )

        response_text = ""
        if response.content:
            for block in response.content: # Response content is a list of blocks
                if block.type == "text":
                    response_text += block.text
        if not response_text and response.stop_reason == "error": # Check if it was an error response not caught above
             logger.warning(f"Anthropic response for {request_id} indicated an error stop reason but no error was caught: {response.stop_reason}")
             response_text = f"Anthropic API indicated an error: {response.stop_reason}"
        elif not response_text:
            logger.warning(f"Anthropic response for {request_id} had no text content blocks. Stop reason: {response.stop_reason}")
            response_text = f"No text content in Anthropic response (stop_reason: {response.stop_reason})."


        response_text_content = MCPTextContent(text=response_text)

        return CreateMessageResult(
            role="assistant",
            content=response_text_content,
            model=response.model,
            stopReason=response.stop_reason if response.stop_reason else "UNKNOWN",
            _meta={
                "id": response.id,
                "usage": {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
                "anthropic_stop_sequence": response.stop_sequence,
                "anthropic_response_role": response.role,
            }
        )

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        if not isinstance(mcp_request_model, CreateMessageRequest):
            logger.warning(f"Streaming not supported for {type(mcp_request_model).__name__} by AnthropicDriver.")
            yield MCPPartialResponse(
                error={"code": -32600, "message": f"Streaming not supported for {type(mcp_request_model).__name__}"},
                is_final_chunk=True); return

        request_params = mcp_request_model.params
        anthropic_model_name = request_params.metadata.get("anthropic_model_name", "claude-3-haiku-20240307")

        if self.test_mode or self.mock_responses:
            logger.info(f"AnthropicDriver streaming mock response for request_id: {request_id}")
            mock_stream_parts = ["Anthropic mock stream 1 ", "Anthropic mock stream 2 final."]
            for i, part in enumerate(mock_stream_parts):
                await asyncio.sleep(0.01)
                yield MCPPartialResponse(
                    partial_text=part,
                    is_final_chunk=(i == len(mock_stream_parts) - 1),
                    metadata={"request_id": request_id}
                );
            return

        anthropic_messages = self._mcp_to_anthropic_messages(request_params.messages)
        system_prompt = self._get_system_prompt(request_params.messages)

        if not anthropic_messages:
             logger.warning(f"Anthropic stream {request_id} requires at least one user or assistant message.")
             yield MCPPartialResponse(error={"code": -32600, "message": "Anthropic stream requires valid user/assistant messages."}, is_final_chunk=True); return

        api_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
        }
        if request_params.metadata and "anthropic_params" in request_params.metadata:
             extra_params = request_params.metadata["anthropic_params"]
             if isinstance(extra_params, dict):
                try:
                    valid_extra_params = AnthropicChatParameters(**extra_params).model_dump(exclude_none=True)
                    api_params.update(valid_extra_params)
                except Exception as e:
                     logger.warning(f"Invalid Anthropic stream parameters in metadata for {request_id}: {e}")

        api_params = {k: v for k, v in api_params.items() if v is not None}
        if "max_tokens" not in api_params or api_params["max_tokens"] is None:
            api_params["max_tokens"] = 1024

        message_id_from_start_event = None
        final_usage_from_delta_event = None
        final_stop_reason_from_delta_event = None

        try:
            logger.debug(f"Streaming from Anthropic (req_id: {request_id}): model={anthropic_model_name}, messages_count={len(anthropic_messages)}, system_present={bool(system_prompt)}, params={api_params}")
            async with self.client.messages.stream( # Use context manager for proper resource handling
                model=anthropic_model_name,
                messages=anthropic_messages,
                system=system_prompt if system_prompt else None,
                **api_params,
            ) as stream:
                async for event in stream:
                    if event.type == "message_start":
                        message_id_from_start_event = event.message.id
                        # Initial input tokens are known at start
                        final_usage_from_delta_event = {"input_tokens": event.message.usage.input_tokens, "output_tokens": 0}
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield MCPPartialResponse(
                                partial_text=event.delta.text,
                                metadata={"request_id": request_id, "anthropic_message_id": message_id_from_start_event},
                                is_final_chunk=False,
                            )
                    elif event.type == "message_delta":
                        # This event gives stop_reason and final output_tokens count
                        if final_usage_from_delta_event: # Should always be true after message_start
                             final_usage_from_delta_event["output_tokens"] = event.usage.output_tokens
                        final_stop_reason_from_delta_event = event.delta.stop_reason
                    # message_stop event indicates the end of all events for that message.
                    # We will send the final chunk *after* the loop finishes processing all events.

            # After stream is fully processed (outside the `async for event in stream` loop, but still in `async with` if possible, or directly after)
            final_metadata = {
                "request_id": request_id,
                "anthropic_message_id": message_id_from_start_event,
                "finish_reason": final_stop_reason_from_delta_event or "UNKNOWN",
            }
            if final_usage_from_delta_event:
                final_metadata["usage"] = final_usage_from_delta_event

            yield MCPPartialResponse(
                partial_text="",
                metadata=final_metadata,
                is_final_chunk=True,
            )

        except Exception as e:
            logger.error(f"Anthropic API Error during stream for request_id {request_id}: {e}", exc_info=True)
            yield MCPPartialResponse(error={"message": f"Anthropic API Error during stream: {str(e)}"}, is_final_chunk=True)

    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        logger.debug(f"AnthropicDriver received notification: {mcp_notification_model.method} for request_id: {request_id}")
        pass
