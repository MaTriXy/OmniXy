import google.generativeai as genai
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

# Gemini specific parameter validation
class GeminiGenerationConfig(BaseModel):
    temperature: Optional[float] = Field(None)
    max_output_tokens: Optional[int] = Field(None)
    top_p: Optional[float] = Field(None)
    top_k: Optional[int] = Field(None)
    stop_sequences: Optional[List[str]] = Field(None)
    # candidate_count: Optional[int] = Field(None) # Usually 1 for chat

class GeminiSafetySetting(BaseModel): # Renamed from GeminiSafetySettings to avoid Pydantic conflict with list
    category: str # e.g., "HARM_CATEGORY_HARASSMENT"
    threshold: str # e.g., "BLOCK_MEDIUM_AND_ABOVE"


class GeminiDriver:
    # MODEL_ID = "gemini-pro" # Default model, can be overridden by request metadata

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)
        self.api_key = config.get("api_key")
        self._model_instance_cache: Dict[str, genai.GenerativeModel] = {}


        if not self.test_mode and not self.mock_responses:
            if not self.api_key:
                raise ValueError("Gemini API key is required when not in test/mock mode.")
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to configure Gemini SDK: {e}")
                raise

    def _get_model_instance(self, model_name: str) -> genai.GenerativeModel:
        if model_name not in self._model_instance_cache:
            try:
                self._model_instance_cache[model_name] = genai.GenerativeModel(model_name)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model {model_name}: {e}")
                raise ValueError(f"Invalid Gemini model name or configuration issue: {model_name}") from e
        return self._model_instance_cache[model_name]

    def _mcp_to_gemini_contents(self, mcp_messages: List[MCPSamplingMessage]) -> List[Dict[str, Any]]:
        gemini_contents = []
        system_instruction_parts = []

        for msg in mcp_messages:
            role = "user" if msg.role == "user" else "model" # Gemini uses 'model' for assistant

            # Handle system messages: Gemini prefers them as system_instruction at the start
            if msg.role == "system" and isinstance(msg.content, MCPTextContent):
                system_instruction_parts.append({"text": msg.content.text})
                continue # System instructions are handled separately

            current_parts = []
            if isinstance(msg.content, MCPTextContent):
                current_parts.append({"text": msg.content.text})
            elif isinstance(msg.content, MCPImageContent):
                # Assuming base64 data for inline_data
                current_parts.append({"inline_data": {"mime_type": msg.content.mimeType, "data": msg.content.data}})
            else:
                logger.warning(f"GeminiDriver skipping unsupported MCP content type: {type(msg.content)}")
                continue

            if current_parts:
                gemini_contents.append({"role": role, "parts": current_parts})

        # Prepend system instructions if any.
        # Note: The `system_instruction` parameter for `GenerativeModel` is a more direct way.
        # If we use that, system messages shouldn't be in `contents`.
        # For this conversion, we'll assume they are mixed in if `system_instruction` isn't used at call site.
        # However, the preferred method is to pass `system_instruction` to `GenerativeModel` constructor or `generate_content`.
        # This function just prepares the `contents` list. The caller should handle system_instruction.
        return gemini_contents

    def _prepare_system_instruction(self, mcp_messages: List[MCPSamplingMessage]) -> Optional[Dict[str, Any]]:
        # Extracts system messages to be used with Gemini's `system_instruction` parameter.
        system_texts = []
        for msg in mcp_messages:
            if msg.role == "system" and isinstance(msg.content, MCPTextContent):
                system_texts.append(msg.content.text)
        if system_texts:
            # Concatenate multiple system messages if present
            return {"parts": [{"text": "\n".join(system_texts)}]}
        return None


    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        if isinstance(mcp_request_model, CreateMessageRequest):
            return await self._handle_create_message(mcp_request_model, request_id)
        else:
            logger.error(f"GeminiDriver received unsupported request type: {type(mcp_request_model).__name__}")
            raise NotImplementedError(
                f"GeminiDriver does not support request type: {type(mcp_request_model).__name__}"
            )

    async def _handle_create_message(
        self, request_container: CreateMessageRequest, request_id: RequestId
    ) -> CreateMessageResult:
        request_params = request_container.params
        gemini_model_name = request_params.metadata.get("gemini_model_name", "gemini-1.5-flash-latest")

        if self.test_mode or self.mock_responses:
            logger.info(f"GeminiDriver running in test/mock mode for request_id: {request_id}")
            mock_text_content = MCPTextContent(text="This is a mock response from Gemini for testing purposes.")
            return CreateMessageResult(
                role="assistant",
                content=mock_text_content,
                model=gemini_model_name,
                stopReason="STOP",
                _meta={
                    "id": f"mock-gemini-resp-{request_id}",
                    "usage": {"prompt_token_count": 5, "candidates_token_count": 5, "total_token_count": 10}
                }
            )

        # Filter out system messages for main content, prepare system_instruction separately
        user_and_assistant_messages = [m for m in request_params.messages if m.role != "system"]
        gemini_contents = self._mcp_to_gemini_contents(user_and_assistant_messages)
        system_instruction = self._prepare_system_instruction(request_params.messages)


        if not gemini_contents and not system_instruction: # Must have some content
             logger.warning("Gemini request requires valid content parts or system instruction.")
             # Return an error-like CreateMessageResult
             return CreateMessageResult(role="assistant", content=MCPTextContent(text="Error: No valid content for Gemini request."), model=gemini_model_name, stopReason="ERROR")


        model_instance = self._get_model_instance(gemini_model_name)
        if system_instruction: # Re-initialize model with system instruction if present
             try:
                model_instance = genai.GenerativeModel(gemini_model_name, system_instruction=system_instruction)
             except Exception as e:
                logger.error(f"Failed to initialize Gemini model {gemini_model_name} with system instruction: {e}")
                # Fallback or error
                return CreateMessageResult(role="assistant", content=MCPTextContent(text=f"Error: Failed to set system instruction for {gemini_model_name}."), model=gemini_model_name, stopReason="ERROR")


        gen_config_dict = {
            "temperature": request_params.temperature,
            "max_output_tokens": request_params.maxTokens,
        }
        safety_settings_list = []

        if request_params.metadata:
            if "gemini_generation_config" in request_params.metadata:
                cfg = request_params.metadata["gemini_generation_config"]
                if isinstance(cfg, dict):
                    valid_cfg = GeminiGenerationConfig(**cfg).model_dump(exclude_none=True)
                    gen_config_dict.update(valid_cfg)

            if "gemini_safety_settings" in request_params.metadata:
                ss = request_params.metadata["gemini_safety_settings"]
                if isinstance(ss, list):
                    for item in ss:
                        if isinstance(item, dict):
                            try:
                                safety_settings_list.append(GeminiSafetySetting(**item).model_dump())
                            except Exception as e:
                                logger.warning(f"Invalid safety setting item: {item}, error: {e}")

        gen_config_obj = genai.types.GenerationConfig(**{k:v for k,v in gen_config_dict.items() if v is not None})
        safety_settings_obj = safety_settings_list if safety_settings_list else None

        try:
            logger.debug(f"Sending to Gemini: model={gemini_model_name}, contents={gemini_contents[:2]}, config={gen_config_obj}, safety={safety_settings_obj}")
            response = await model_instance.generate_content_async(
                contents=gemini_contents if gemini_contents else None, # Pass None if only system_instruction is used
                generation_config=gen_config_obj,
                safety_settings=safety_settings_obj,
            )
        except Exception as e:
            logger.error(f"Gemini API Error for request_id {request_id}: {e}", exc_info=True)
            error_text = f"Error from Gemini: {type(e).__name__} - {str(e)}"
            # Try to get more specific stop reason
            stop_reason_val = "ERROR"
            if hasattr(e, 'message') and "SAFETY" in e.message.upper(): # Basic check
                stop_reason_val = "SAFETY"

            return CreateMessageResult(
                role="assistant", content=MCPTextContent(text=error_text), model=gemini_model_name,
                stopReason=stop_reason_val, _meta={"id": f"error-gemini-resp-{request_id}", "error_details": str(e)}
            )

        response_text = ""
        # Check if response.text exists, otherwise iterate parts
        if hasattr(response, 'text') and response.text:
            response_text = response.text
        elif response.parts:
            response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        else:
            logger.warning(f"Gemini response for {request_id} had no text attribute or text parts.")
            # Check for blocked prompt
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 response_text = f"Content generation blocked due to: {response.prompt_feedback.block_reason.name}"


        response_text_content = MCPTextContent(text=response_text or "No text content in Gemini response.")

        finish_reason_val = "UNKNOWN"
        if response.candidates and response.candidates[0].finish_reason:
            finish_reason_val = response.candidates[0].finish_reason.name
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
             finish_reason_val = f"BLOCKED_{response.prompt_feedback.block_reason.name}"

        usage_info = {"prompt_token_count": None, "candidates_token_count": None, "total_token_count": None}
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage_info = {
                "prompt_token_count": response.usage_metadata.prompt_token_count,
                "candidates_token_count": response.usage_metadata.candidates_token_count if hasattr(response.usage_metadata, 'candidates_token_count') else None, # some models might not have this
                "total_token_count": response.usage_metadata.total_token_count,
            }

        return CreateMessageResult(
            role="assistant", content=response_text_content, model=gemini_model_name,
            stopReason=finish_reason_val,
            _meta={
                "id": f"gemini-resp-{request_id}",
                "usage": usage_info,
                "gemini_finish_reason_details": finish_reason_val,
                "gemini_safety_ratings": [{"category": sr.category.name, "probability": sr.probability.name} for sr in response.candidates[0].safety_ratings] if response.candidates and response.candidates[0].safety_ratings else None,
                "prompt_feedback_block_reason": response.prompt_feedback.block_reason.name if response.prompt_feedback and response.prompt_feedback.block_reason else None
            }
        )

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        if not isinstance(mcp_request_model, CreateMessageRequest):
            logger.warning(f"Streaming not supported for {type(mcp_request_model).__name__} by GeminiDriver.")
            yield MCPPartialResponse(
                error={"code": -32600, "message": f"Streaming not supported for {type(mcp_request_model).__name__}"},
                is_final_chunk=True
            )
            return

        request_params = mcp_request_model.params
        gemini_model_name = request_params.metadata.get("gemini_model_name", "gemini-1.5-flash-latest")

        if self.test_mode or self.mock_responses:
            logger.info(f"GeminiDriver streaming mock response for request_id: {request_id}")
            mock_stream_parts = ["Gemini mock stream part 1 ", "Gemini mock stream part 2 final."]
            for i, part in enumerate(mock_stream_parts):
                await asyncio.sleep(0.01)
                yield MCPPartialResponse(
                    partial_text=part,
                    is_final_chunk=(i == len(mock_stream_parts) - 1),
                    metadata={"request_id": request_id}
                )
            return

        user_and_assistant_messages = [m for m in request_params.messages if m.role != "system"]
        gemini_contents = self._mcp_to_gemini_contents(user_and_assistant_messages)
        system_instruction = self._prepare_system_instruction(request_params.messages)

        if not gemini_contents and not system_instruction:
            logger.warning("Gemini stream requires valid content or system instruction.")
            yield MCPPartialResponse(error={"code": -32600, "message": "Gemini stream requires valid content."}, is_final_chunk=True)
            return

        model_instance = self._get_model_instance(gemini_model_name)
        if system_instruction:
            try:
                model_instance = genai.GenerativeModel(gemini_model_name, system_instruction=system_instruction)
            except Exception as e:
                logger.error(f"Failed to set system instruction for streaming with {gemini_model_name}: {e}")
                yield MCPPartialResponse(error={"message": f"Error setting system instruction for {gemini_model_name} stream."}, is_final_chunk=True)
                return


        gen_config_dict = {
            "temperature": request_params.temperature,
            "max_output_tokens": request_params.maxTokens,
        }
        if request_params.metadata and "gemini_generation_config" in request_params.metadata:
            cfg = request_params.metadata["gemini_generation_config"]
            if isinstance(cfg, dict):
                gen_config_dict.update(GeminiGenerationConfig(**cfg).model_dump(exclude_none=True))

        gen_config_obj = genai.types.GenerationConfig(**{k:v for k,v in gen_config_dict.items() if v is not None})
        safety_settings_obj = None # Simplified for stream example

        try:
            logger.debug(f"Streaming from Gemini: model={gemini_model_name}, contents={gemini_contents[:2]}, config={gen_config_obj}")
            response_stream = await model_instance.generate_content_async(
                contents=gemini_contents if gemini_contents else None,
                generation_config=gen_config_obj,
                safety_settings=safety_settings_obj,
                stream=True
            )
            async for chunk in response_stream:
                chunk_text = ""
                # Gemini stream chunks might not have .text directly, but .parts
                if chunk.parts:
                    chunk_text = "".join(part.text for part in chunk.parts if hasattr(part, 'text'))
                elif hasattr(chunk, 'text') and chunk.text: # Fallback for simpler text chunks
                     chunk_text = chunk.text

                # Check for blocked prompt feedback in chunks
                if chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                    logger.warning(f"Gemini stream chunk blocked for request_id {request_id}, reason: {chunk.prompt_feedback.block_reason.name}")
                    yield MCPPartialResponse(
                        partial_text=f"Content generation blocked by API: {chunk.prompt_feedback.block_reason.name}",
                        metadata={"request_id": request_id, "finish_reason": f"BLOCKED_{chunk.prompt_feedback.block_reason.name}"},
                        is_final_chunk=True # Stop streaming if blocked
                    )
                    return # End the generator

                if chunk_text:
                    yield MCPPartialResponse(
                        partial_text=chunk_text,
                        metadata={"request_id": request_id},
                        is_final_chunk=False,
                    )
            # After loop, indicate stream completion.
            # The actual finish_reason and usage comes from the complete aggregated response,
            # not typically available per chunk or at the very end of basic stream iter.
            # For a more robust solution, one might need to call generate_content (non-stream)
            # again or inspect the last chunk if it contains summary.
            # For now, a generic "STREAM_END".
            yield MCPPartialResponse(partial_text="", is_final_chunk=True, metadata={"request_id": request_id, "finish_reason": "STREAM_COMPLETE"})

        except Exception as e:
            logger.error(f"Gemini API Error during stream for request_id {request_id}: {e}", exc_info=True)
            yield MCPPartialResponse(error={"message": f"Gemini API Error during stream: {str(e)}"}, is_final_chunk=True)


    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        logger.debug(f"GeminiDriver received notification: {mcp_notification_model.method} for request_id: {request_id}")
        pass
