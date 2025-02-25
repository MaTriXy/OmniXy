import cohere
from src.core.response import MCPResponse, MCPPartialResponse


class CohereDriver:
    def __init__(self, config=None):
        config = config or {}
        self.test_mode = config.get("test_mode", False)
        self.mock_responses = config.get("mock_responses", False)

        # Only initialize the client if not in test mode
        if not self.test_mode and not self.mock_responses:
            api_key = config.get("api_key", "")
            self.client = cohere.Client(api_key=api_key)

    def send_request(self, mcp_request):
        # Always return mock response in test mode
        if self.test_mode or self.mock_responses:
            # Return a mock response in the format expected by tests
            return {
                "id": "mock-response-id",
                "text": "This is a mock response from Cohere for testing purposes.",
                "model": mcp_request.model,
                "tokens_used": 10,
            }

        # Only make API calls if not in test mode
        # Convert messages to Cohere format
        prompt = ""
        for msg in mcp_request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            else:
                prompt += f"{content}\n"

        # Extract parameters from the request
        params = mcp_request.parameters.copy() if mcp_request.parameters else {}

        # Remove any parameters that are not supported by Cohere
        for param in list(params.keys()):
            if param not in [
                "temperature",
                "max_tokens",
                "p",
                "frequency_penalty",
                "presence_penalty",
            ]:
                del params[param]

        response = self.client.generate(
            model=mcp_request.model, prompt=prompt, **params
        )

        return MCPResponse(
            text=response.generations[0].text,
            metadata={
                "model": mcp_request.model,
                "tokens_used": response.meta.billed_units.input_tokens
                + response.meta.billed_units.output_tokens,
            },
        )

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
        response = self.client.chat(
            message=mcp_request.messages[-1]["content"],
            model=mcp_request.model,
            stream=True,
            **mcp_request.parameters,
        )
        for chunk in response:
            if chunk.text:
                yield MCPPartialResponse(partial_text=chunk.text)
