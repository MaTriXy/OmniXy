import asyncio
import logging
from typing import Optional, AsyncIterator, Dict, Any, List
from pydantic import BaseModel, Field # For local LLM specific params if needed

from src.core.response import MCPPartialResponse, CreateMessageResult, BaseResult
from src.core.request import (
    MCPRequest,
    CreateMessageRequest,
    RequestId,
    SamplingMessage as MCPSamplingMessage,
    TextContent as MCPTextContent,
)

logger = logging.getLogger(__name__)

# Example: Parameters for a local LLM via llama-cpp-python or similar
class LocalLLMParams(BaseModel):
    temperature: Optional[float] = Field(None)
    max_tokens: Optional[int] = Field(None) # Note: some local LLMs use n_predict
    top_p: Optional[float] = Field(None)
    top_k: Optional[int] = Field(None)
    stop: Optional[List[str]] = Field(None)
    # Add other common params like repeat_penalty, presence_penalty etc.
    # model_name_or_alias: Optional[str] = None # If this driver can handle multiple local models


class LocalLLMDriver:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.model_path = config.get("model_path") # Path to GGUF file or similar
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)

        self.llm_instance = None # Placeholder for the actual loaded LLM (e.g., Llama instance)

        if not self.test_mode and not self.mock_responses:
            if not self.model_path:
                logger.warning("LocalLLMDriver: model_path not provided. Driver will only work in mock/test mode or if model loaded later.")
            else:
                try:
                    # Placeholder: Actual LLM loading logic
                    # from llama_cpp import Llama
                    # self.llm_instance = Llama(model_path=self.model_path, verbose=False)
                    logger.info(f"LocalLLMDriver: Placeholder for loading model from {self.model_path}")
                    # Simulate loading for now if llama_cpp is not a direct dependency for all tests
                    if "mock_successful_load" in config: # for testing this path without llama_cpp
                        self.llm_instance = object() # Represents a loaded model
                    else:
                        logger.warning("LocalLLMDriver: Actual model loading (e.g., llama-cpp-python) is not implemented in this placeholder.")

                except ImportError:
                    logger.error("LocalLLMDriver: `llama_cpp` not installed. Please install it to use local LLMs.")
                    self.llm_instance = None # Ensure it's None if import fails
                except Exception as e:
                    logger.error(f"LocalLLMDriver: Failed to load model from {self.model_path}: {e}")
                    self.llm_instance = None


    async def execute_mcp_request(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> BaseResult:
        if isinstance(mcp_request_model, CreateMessageRequest):
            return await self._handle_create_message(mcp_request_model, request_id)
        else:
            logger.error(f"LocalLLMDriver received unsupported request type: {type(mcp_request_model).__name__}")
            raise NotImplementedError(
                f"LocalLLMDriver does not support request type: {type(mcp_request_model).__name__}"
            )

    async def _handle_create_message(
        self, request_container: CreateMessageRequest, request_id: RequestId
    ) -> CreateMessageResult:
        request_params = request_container.params
        # Model name for local might be an alias or derived from model_path
        local_model_identifier = request_params.metadata.get("local_llm_model_alias", self.model_path or "default_local_model")

        if self.test_mode or self.mock_responses or not self.llm_instance:
            mode = "test/mock" if (self.test_mode or self.mock_responses) else "unloaded model"
            logger.info(f"LocalLLMDriver running in {mode} mode for request_id: {request_id}")
            mock_text_content = MCPTextContent(text=f"This is a mock response from LocalLLM ({local_model_identifier}) for testing.")
            return CreateMessageResult(
                role="assistant", content=mock_text_content, model=local_model_identifier,
                stopReason="stop", # Common stop reason for local models
                _meta={"id": f"mock-local-resp-{request_id}", "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}}
            )

        # Prepare prompt for the local LLM
        # This often involves creating a single string with roles, similar to older Anthropic/OpenAI instruct formats
        prompt_str = ""
        # System prompt handling (many local models use a specific format or just prepend)
        system_prompt_parts = [msg.content.text for msg in request_params.messages if msg.role == "system" and isinstance(msg.content, MCPTextContent)]
        if system_prompt_parts:
            prompt_str += "\n".join(system_prompt_parts) + "\n\n"

        for msg in request_params.messages:
            if msg.role != "system" and isinstance(msg.content, MCPTextContent): # Process user/assistant messages
                # Example prompt format, adjust based on the model's expected input
                if msg.role == "user":
                    prompt_str += f"USER: {msg.content.text}\n"
                elif msg.role == "assistant":
                    prompt_str += f"ASSISTANT: {msg.content.text}\n"
        prompt_str += "ASSISTANT:" # Prompt the model to start generating as assistant

        # Prepare parameters for the local LLM
        llm_api_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens, # llama-cpp uses max_tokens or n_predict
        }
        if request_params.metadata and "local_llm_params" in request_params.metadata:
            extra_params = request_params.metadata["local_llm_params"]
            if isinstance(extra_params, dict):
                try:
                    valid_extra_params = LocalLLMParams(**extra_params).model_dump(exclude_none=True)
                    llm_api_params.update(valid_extra_params)
                except Exception as e:
                    logger.warning(f"Invalid LocalLLM parameters in metadata for {request_id}: {e}")

        llm_api_params = {k: v for k, v in llm_api_params.items() if v is not None}
        if "max_tokens" not in llm_api_params or llm_api_params["max_tokens"] is None:
             llm_api_params["max_tokens"] = 256 # Default if not provided

        try:
            logger.debug(f"Sending to LocalLLM (req_id: {request_id}): model_alias={local_model_identifier}, params={llm_api_params}, prompt_start='{prompt_str[:100]}...'")

            # Placeholder: Actual call to self.llm_instance.create_completion or similar
            # response_data = self.llm_instance.create_completion(prompt=prompt_str, **llm_api_params)
            # This needs to be async or run in an executor
            # For this placeholder, we'll simulate a response.
            await asyncio.sleep(0.1) # Simulate async work
            simulated_response_text = f"Simulated response from {local_model_identifier} to: {prompt_str[-50:]}"
            simulated_completion_tokens = len(simulated_response_text.split())
            simulated_prompt_tokens = len(prompt_str.split())

            response_data = {
                "choices": [{"text": simulated_response_text, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": simulated_prompt_tokens, "completion_tokens": simulated_completion_tokens, "total_tokens": simulated_prompt_tokens + simulated_completion_tokens}
            }
            logger.info(f"LocalLLM placeholder response generated for {request_id}.")

        except Exception as e:
            logger.error(f"LocalLLM Error for request_id {request_id}: {e}", exc_info=True)
            error_text = f"Error from LocalLLM ({local_model_identifier}): {type(e).__name__} - {str(e)}"
            return CreateMessageResult(
                role="assistant", content=MCPTextContent(text=error_text), model=local_model_identifier,
                stopReason="ERROR", _meta={"id": f"error-local-resp-{request_id}", "error_details": str(e)}
            )

        response_text = response_data.get("choices", [{}])[0].get("text", "No text from local LLM.")
        response_text_content = MCPTextContent(text=response_text)

        stop_reason = response_data.get("choices", [{}])[0].get("finish_reason", "stop")
        usage_data = response_data.get("usage", {})

        return CreateMessageResult(
            role="assistant", content=response_text_content, model=local_model_identifier,
            stopReason=str(stop_reason).upper(),
            _meta={
                "id": f"local-resp-{request_id}",
                "usage": usage_data, # Structure depends on what llama-cpp or similar provides
            }
        )

    async def stream_mcp_responses(
        self, mcp_request_model: MCPRequest, request_id: RequestId
    ) -> AsyncIterator[MCPPartialResponse]:
        request_params = mcp_request_model.params
        local_model_identifier = request_params.metadata.get("local_llm_model_alias", self.model_path or "default_local_model")

        if self.test_mode or self.mock_responses or not self.llm_instance:
            mode = "test/mock" if (self.test_mode or self.mock_responses) else "unloaded model"
            logger.info(f"LocalLLMDriver streaming mock response ({mode}) for request_id: {request_id}")
            mock_stream_parts = [f"LocalLLM ({local_model_identifier}) mock stream 1 ", "LocalLLM mock stream 2 final."]
            for i, part in enumerate(mock_stream_parts):
                await asyncio.sleep(0.01)
                yield MCPPartialResponse(
                    partial_text=part,
                    is_final_chunk=(i == len(mock_stream_parts) - 1),
                    metadata={"request_id": request_id}
                );
            return

        if not isinstance(mcp_request_model, CreateMessageRequest):
            logger.warning(f"Streaming not supported for {type(mcp_request_model).__name__} by LocalLLMDriver.")
            yield MCPPartialResponse(error={"code": -32600, "message": f"Streaming not supported for {type(mcp_request_model).__name__}"}, is_final_chunk=True); return

        prompt_str = "" # Prepare prompt as in _handle_create_message
        system_prompt_parts = [msg.content.text for msg in request_params.messages if msg.role == "system" and isinstance(msg.content, MCPTextContent)]
        if system_prompt_parts:
            prompt_str += "\n".join(system_prompt_parts) + "\n\n"
        for msg in request_params.messages:
            if msg.role != "system" and isinstance(msg.content, MCPTextContent):
                if msg.role == "user": prompt_str += f"USER: {msg.content.text}\n"
                elif msg.role == "assistant": prompt_str += f"ASSISTANT: {msg.content.text}\n"
        prompt_str += "ASSISTANT:"

        llm_api_params = {
            "temperature": request_params.temperature,
            "max_tokens": request_params.maxTokens,
        }
        if request_params.metadata and "local_llm_params" in request_params.metadata:
            # ... (similar param extraction as in _handle_create_message) ...
            extra_params = request_params.metadata["local_llm_params"]
            if isinstance(extra_params, dict):
                try:
                    valid_extra_params = LocalLLMParams(**extra_params).model_dump(exclude_none=True)
                    llm_api_params.update(valid_extra_params)
                except Exception as e:
                    logger.warning(f"Invalid LocalLLM stream parameters for {request_id}: {e}")
        llm_api_params = {k: v for k, v in llm_api_params.items() if v is not None}
        if "max_tokens" not in llm_api_params or llm_api_params["max_tokens"] is None:
             llm_api_params["max_tokens"] = 256

        try:
            logger.debug(f"Streaming from LocalLLM (req_id: {request_id}): model_alias={local_model_identifier}, params={llm_api_params}, prompt_start='{prompt_str[:100]}...'")
            # Placeholder: Actual call to self.llm_instance.create_completion_stream or similar
            # stream = self.llm_instance(prompt=prompt_str, stream=True, **llm_api_params)
            # for chunk in stream:
            #    delta_text = chunk["choices"][0]["text"]
            #    yield MCPPartialResponse(partial_text=delta_text, metadata={"request_id": request_id}, is_final_chunk=False)

            # Simulated stream for placeholder
            simulated_chunks = [f"Local ({local_model_identifier}) chunk 1 ", "Local chunk 2 ", "Local chunk END."]
            for i, chunk_text in enumerate(simulated_chunks):
                await asyncio.sleep(0.05) # Simulate async work
                yield MCPPartialResponse(
                    partial_text=chunk_text,
                    metadata={"request_id": request_id},
                    is_final_chunk=(i == len(simulated_chunks) -1) # Only last one is final based on this simulation
                )
            if not simulated_chunks: # Ensure at least one final signal if stream was empty
                 yield MCPPartialResponse(partial_text="", metadata={"request_id": request_id, "finish_reason": "STOP"}, is_final_chunk=True)


        except Exception as e:
            logger.error(f"LocalLLM Error during stream for request_id {request_id}: {e}", exc_info=True)
            yield MCPPartialResponse(error={"message": f"LocalLLM Error during stream: {str(e)}"}, is_final_chunk=True)

    async def handle_mcp_notification(self, mcp_notification_model: MCPRequest, request_id: Optional[RequestId] = None) -> None:
        logger.debug(f"LocalLLMDriver received notification: {mcp_notification_model.method} for request_id: {request_id}")
        pass
