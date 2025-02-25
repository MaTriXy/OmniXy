from src.core.response import MCPResponse, MCPPartialResponse


class LocalLLMDriver:
    def __init__(self, model_path):
        self.model_path = model_path
        # Initialize your local LLM here (e.g., using llama.cpp or similar)
        # This is a placeholder, replace with actual initialization code
        print(f"Loading local LLM from {model_path}")

    def send_request(self, mcp_request):
        # Implement the logic to send the request to the local LLM
        # and return an MCPResponse
        print(f"Sending request to local LLM: {mcp_request.messages}")
        return MCPResponse(text="Local LLM Response")

    def stream_tokens(self, mcp_request):
        # Implement the logic to stream tokens from the local LLM
        # and yield MCPPartialResponse objects
        print(f"Streaming tokens from local LLM: {mcp_request.messages}")
        yield MCPPartialResponse(partial_text="Local LLM Token")
