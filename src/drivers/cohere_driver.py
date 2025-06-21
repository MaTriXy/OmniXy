import cohere
import asyncio
from typing import Optional, AsyncIterator, Dict, Any, List
from pydantic import BaseModel, Field

from src.core.response import MCPPartialResponse, CreateMessageResult, BaseResult
from src.core.request import (
    MCPRequest, # Union of specific request types
    CreateMessageRequest,
    RequestId,
    SamplingMessage as MCPSamplingMessage,
    TextContent as MCPTextContent,
)

# Cohere specific parameter validation
class CohereChatParams(BaseModel):
    temperature: Optional[float] = Field(None)
    max_tokens: Optional[int] = Field(None)
    p: Optional[float] = Field(None)
    k: Optional[int] = Field(None)
    frequency_penalty: Optional[float] = Field(None)
    presence_penalty: Optional[float] = Field(None)
    stop_sequences: Optional[List[str]] = Field(None)
    # Cohere model name will be extracted from CreateMessageRequest.params.metadata
    # connectord: Optional[List[Dict[str, Any]]] = None # For Cohere Connectors (RAG)


class CohereDriver:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)
        self.api_key = config.get("api_key")

        if not self.test_mode and not self.mock_responses:
            if not self.api_key:
                raise ValueError("Cohere API key is required when not in test/mock mode.")
            self.client = cohere.AsyncClient(api_key=self.api_key, client_name="omni_mcp_layer")
        else:
            self.client = None

    def _mcp_to_cohere_chat_history(self, mcp_messages: List[MCPSamplingMessage]) -> List[Dict[str, str]]:
        """Converts MCP messages (excluding the last one) to Cohere chat history format."""
        history = []
        # Cohere expects roles "USER" or "CHATBOT".
        # The last message in mcp_messages is the current user query.
        for msg in mcp_messages[:-1]:
            if isinstance(msg.content, MCPTextContent):
                role = "USER" if msg.role == "user" else "CHATBOT"
                history.append({"role": role, "message": msg.content.text})
            else:
                print(f"Warning: CohereDriver skipping non-text content in chat history: {type(msg.content)}")
        return history

    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        if isinstance(mcp_request_model, CreateMessageRequest):
            return await self._handle_create_message(mcp_request_model, request_id)
        else:
            raise NotImplementedError(
                f"CohereDriver does not support request type: {type(mcp_request_model).__name__}"
            )

    async def _handle_create_message(
        self, request_container: CreateMessageRequest, request_id: RequestId
    ) -> CreateMessageResult:
        request_params = request_container.params

        # Determine Cohere model name
        cohere_model_name = request_params.metadata.get("cohere_model_name", "command-r") # Default model

        if self.test_mode or self.mock_responses:
            mock_text_content = MCPTextContent(text="This is a mock response from Cohere for testing purposes.")
            # Cohere's finish_reason is usually 'COMPLETE' or 'MAX_TOKENS' or 'ERROR'
            return CreateMessageResult(
                role="assistant",
                content=mock_text_content,
                model=cohere_model_name,
                stopReason="COMPLETE",
                _meta={
                    "id": f"mock-cohere-resp-{request_id}",
                    "usage": {"input_tokens": 5, "output_tokens": 5, "total_tokens": 10} # Simplified
                }
            )

        if not request_params.messages or not isinstance(request_params.messages[-1].content, MCPTextContent):
            raise ValueError("Cohere request requires at least one text message as the current query.")

        current_user_message = request_params.messages[-1].content.text
        chat_history = self._mcp_to_cohere_chat_history(request_params.messages)

        # Prepare Cohere-specific parameters
        cohere_api_params = {
            "temperature": request_params.temperature, # Directly from CreateMessageRequest
            "max_tokens": request_params.maxTokens,   # Directly from CreateMessageRequest
        }
        # Add other params from metadata if they exist and are valid for CohereChatParams
        if request_params.metadata and "cohere_params" in request_params.metadata:
            extra_params = request_params.metadata["cohere_params"]
            if isinstance(extra_params, dict):
                valid_extra_params = CohereChatParams(**extra_params).model_dump(exclude_none=True)
                cohere_api_params.update(valid_extra_params)

        # Ensure no None values are passed if Cohere SDK expects them to be absent
        cohere_api_params = {k: v for k, v in cohere_api_params.items() if v is not None}

        try:
            response = await self.client.chat(
                model=cohere_model_name,
                message=current_user_message,
                chat_history=chat_history if chat_history else None,
                **cohere_api_params,
            )
        except cohere.CohereAPIError as e:
            # Handle API errors from Cohere, convert to an error result if MCPLayer expects it
            # For now, re-raise or wrap, depending on MCPLayer's error handling strategy
            print(f"Cohere API Error: {e}")
            raise # Or return a structured error result

        response_text_content = MCPTextContent(text=response.text)

        input_tokens = 0
        output_tokens = 0
        if response.meta and response.meta.billed_units: # Cohere v4 style
            input_tokens = response.meta.billed_units.input_tokens or 0
            output_tokens = response.meta.billed_units.output_tokens or 0
        elif response.meta and response.meta.tokens: # Cohere v5 style (AsyncClient)
            input_tokens = response.meta.tokens.input_tokens or 0
            output_tokens = response.meta.tokens.output_tokens or 0

        return CreateMessageResult(
            role="assistant", # MCP standard role
            content=response_text_content,
            model=cohere_model_name, # Cohere chat response doesn't always repeat the model name
            stopReason=str(response.finish_reason).upper() if response.finish_reason else "UNKNOWN",
            _meta={
                "id": response.response_id,
                "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens},
                "cohere_documents": response.documents, # If RAG was used
                "cohere_search_results": response.search_results, # If RAG was used
                "cohere_search_queries": response.search_queries, # If RAG was used
            }
        )

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        if not isinstance(mcp_request_model, CreateMessageRequest):
            yield MCPPartialResponse(
                error={"code": -32600, "message": f"Streaming not supported for {type(mcp_request_model).__name__}"},
                is_final_chunk=True
            )
            return

        request_params = mcp_request_model.params
        cohere_model_name = request_params.metadata.get("cohere_model_name", "command-r")

        if self.test_mode or self.mock_responses:
            mock_stream_parts = ["This ", "is ", "a mock Cohere ", "streaming ", "response."]
            for i, part in enumerate(mock_stream_parts):
                await asyncio.sleep(0.01)
                yield MCPPartialResponse(
                    partial_text=part,
                    is_final_chunk=(i == len(mock_stream_parts) - 1),
                    metadata={"request_id": request_id}
                )
            return

        if not request_params.messages or not isinstance(request_params.messages[-1].content, MCPTextContent):
            yield MCPPartialResponse(
                error={"code": -32600, "message": "Cohere stream requires at least one text message as current query."},
                is_final_chunk=True
            )
            return

        current_user_message = request_params.messages[-1].content.text
        chat_history = self._mcp_to_cohere_chat_history(request_params.messages)

        cohere_api_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
        }
        if request_params.metadata and "cohere_params" in request_params.metadata:
            extra_params = request_params.metadata["cohere_params"]
            if isinstance(extra_params, dict):
                valid_extra_params = CohereChatParams(**extra_params).model_dump(exclude_none=True)
                cohere_api_params.update(valid_extra_params)
        cohere_api_params = {k: v for k, v in cohere_api_params.items() if v is not None}

        try:
            stream = self.client.chat_stream( # Correct method for AsyncClient v5
                model=cohere_model_name,
                message=current_user_message,
                chat_history=chat_history if chat_history else None,
                **cohere_api_params
            )
            async for event in stream:
                event_response_id = None # Placeholder for response_id if available per event
                if event.event_type == "text-generation":
                    yield MCPPartialResponse(
                        partial_text=event.text,
                        metadata={"request_id": request_id, "cohere_event_index": event.index if hasattr(event, 'index') else None},
                        is_final_chunk=False,
                    )
                elif event.event_type == "stream-end":
                    final_metadata = {
                        "request_id": request_id,
                        "finish_reason": str(event.finish_reason).upper() if event.finish_reason else "UNKNOWN",
                    }
                    # For Cohere v5, token counts are in the final response object within the event
                    if event.response and event.response.meta and event.response.meta.tokens:
                        tokens = event.response.meta.tokens
                        final_metadata["usage"] = {
                             "input_tokens": tokens.input_tokens or 0,
                             "output_tokens": tokens.output_tokens or 0,
                             "total_tokens": (tokens.input_tokens or 0) + (tokens.output_tokens or 0)
                        }
                    elif event.response and event.response.meta and event.response.meta.billed_units: # Older style
                         billed_units = event.response.meta.billed_units
                         final_metadata["usage"] = {
                             "input_tokens": billed_units.input_tokens or 0,
                             "output_tokens": billed_units.output_tokens or 0,
                             "total_tokens": (billed_units.input_tokens or 0) + (billed_units.output_tokens or 0)
                         }


                    yield MCPPartialResponse(
                        partial_text="",
                        metadata=final_metadata,
                        is_final_chunk=True,
                    )
                # Handle other event types like 'citation-generation', 'tool-calls-generation' if needed
        except cohere.CohereAPIError as e:
            yield MCPPartialResponse(error={"message": f"Cohere API Error during stream: {str(e)}"}, is_final_chunk=True)
        except Exception as e:
            yield MCPPartialResponse(error={"message": f"Unexpected error during Cohere stream: {str(e)}"}, is_final_chunk=True)


    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        # print(f"CohereDriver received notification: {mcp_notification_model.method}")
        pass
