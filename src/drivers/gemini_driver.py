from src.core.response import MCPResponse, MCPPartialResponse
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


class GeminiDriver:
    MODEL_ID = "gemini-2.0-flash-001"  # @param {type: "string"}

    def __init__(self, config=None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)

        # Only initialize the client if not in test mode
        if not self.test_mode and not self.mock_responses:
            api_key = config.get("api_key", "")
            genai.configure(api_key=api_key)

    def send_request(self, mcp_request):
        # Always return mock response in test mode
        if self.test_mode or self.mock_responses:
            # Return a mock response in the format expected by tests
            return {
                "id": "mock-response-id",
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "This is a mock response from Gemini for testing purposes."
                                }
                            ]
                        },
                        "finish_reason": "STOP",
                    }
                ],
                "model": mcp_request.model,
                "usage_metadata": {"total_token_count": 10},
            }

        # Only make API calls if not in test mode
        model = genai.GenerativeModel(model_name=mcp_request.model)

        # Convert messages to Gemini format
        gemini_messages = []
        for msg in mcp_request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                # Gemini doesn't have a system role, so prepend it to the first user message
                gemini_messages.append(
                    {"role": "user", "parts": [{"text": f"System: {content}"}]}
                )
            elif role == "user":
                gemini_messages.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [{"text": content}]})

        response = model.generate_content(gemini_messages, **mcp_request.parameters)

        return MCPResponse(text=response.text, metadata={"model": mcp_request.model})

    def stream_tokens(self, mcp_request):
        # Always return mock streaming responses in test mode
        if self.test_mode or self.mock_responses:
            yield MCPPartialResponse(partial_text="This ")
            yield MCPPartialResponse(partial_text="is ")
            yield MCPPartialResponse(partial_text="a ")
            yield MCPPartialResponse(partial_text="mock ")
            yield MCPPartialResponse(partial_text="streaming ")
            yield MCPPartialResponse(partial_text="response.")
            return

        # Only make API calls if not in test mode
        model = genai.GenerativeModel(model_name=mcp_request.model)

        # Convert MCP messages to Gemini format
        gemini_messages = []
        for msg in mcp_request.messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [msg["content"]]})

        response = model.generate_content(
            gemini_messages, stream=True, **mcp_request.parameters
        )

        for chunk in response:
            if chunk.text:
                yield MCPPartialResponse(partial_text=chunk.text)
