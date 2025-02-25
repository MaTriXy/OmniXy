# Provider Drivers

Provider drivers translate generic MCP requests into provider-specific API calls and process responses back into the MCP structure.

## Driver Interface

All provider drivers must implement the `BaseLLMDriver` interface:

```python
class BaseLLMDriver:
    def __init__(self, credentials: dict, config: dict):
        self.credentials = credentials
        self.config = config
        self.validate_setup()

    def validate_setup(self) -> bool:
        """Validate driver configuration."""
        raise NotImplementedError

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        """Send a single request to the provider."""
        raise NotImplementedError

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        """Stream tokens from the provider."""
        raise NotImplementedError

    def batch_requests(self, requests: List[MCPRequest]) -> List[MCPResponse]:
        """Process multiple requests efficiently."""
        raise NotImplementedError

    def validate_request(self, mcp_request: MCPRequest) -> bool:
        """Validate request against provider constraints."""
        raise NotImplementedError
```

## Provider Implementations

### Gemini Driver

```python
class GeminiDriver(BaseLLMDriver):
    def __init__(self, credentials: dict, config: dict):
        super().__init__(credentials, config)
        self.client = google.generativeai.GenerativeModel(
            model_name=config.get("model", "gemini-pro")
        )

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        response = self.client.generate_content(
            mcp_request.messages[-1]["content"],
            generation_config=self._get_generation_config(mcp_request)
        )
        return self._convert_to_mcp_response(response)

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        stream = self.client.generate_content(
            mcp_request.messages[-1]["content"],
            generation_config=self._get_generation_config(mcp_request),
            stream=True
        )
        for chunk in stream:
            yield self._convert_to_mcp_partial(chunk)
```

### OpenAI Driver

```python
class OpenAIDriver(BaseLLMDriver):
    def __init__(self, credentials: dict, config: dict):
        super().__init__(credentials, config)
        self.client = openai.OpenAI(api_key=credentials["api_key"])

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        response = self.client.chat.completions.create(
            model=mcp_request.model,
            messages=mcp_request.messages,
            **self._get_completion_args(mcp_request)
        )
        return self._convert_to_mcp_response(response)

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        stream = self.client.chat.completions.create(
            model=mcp_request.model,
            messages=mcp_request.messages,
            stream=True,
            **self._get_completion_args(mcp_request)
        )
        for chunk in stream:
            yield self._convert_to_mcp_partial(chunk)
```

### Cohere Driver

```python
class CohereDriver(BaseLLMDriver):
    def __init__(self, credentials: dict, config: dict):
        super().__init__(credentials, config)
        self.client = cohere.Client(api_key=credentials["api_key"])

    def send_request(self, mcp_request: MCPRequest) -> MCPResponse:
        response = self.client.generate(
            prompt=self._convert_messages_to_prompt(mcp_request.messages),
            **self._get_generation_params(mcp_request)
        )
        return self._convert_to_mcp_response(response)

    def stream_tokens(self, mcp_request: MCPRequest) -> Iterator[MCPPartialResponse]:
        stream = self.client.generate(
            prompt=self._convert_messages_to_prompt(mcp_request.messages),
            stream=True,
            **self._get_generation_params(mcp_request)
        )
        for chunk in stream:
            yield self._convert_to_mcp_partial(chunk)
```

## Plugin Integration

Drivers can be extended through plugins:

```python
class CustomProviderPlugin(ProviderPlugin):
    def pre_request(self, mcp_request: MCPRequest) -> MCPRequest:
        """Modify request before sending to provider."""
        return mcp_request

    def post_response(self, mcp_response: MCPResponse) -> MCPResponse:
        """Process response after receiving from provider."""
        return mcp_response

# Register plugin
plugin_manager.register_provider_plugin("custom_provider", CustomProviderPlugin())
```

## Adding a New Driver

1. Create a new class inheriting from `BaseLLMDriver`
2. Implement all required methods
3. Add provider-specific configuration
4. Implement proper error handling
5. Add comprehensive tests
6. Document provider-specific features
7. Register with plugin manager if needed

## Best Practices

1. **Error Handling**
   - Implement proper retries
   - Convert provider errors to MCP errors
   - Log detailed error information

2. **Performance**
   - Use connection pooling
   - Implement request batching
   - Cache responses when appropriate

3. **Security**
   - Validate all inputs
   - Sanitize responses
   - Handle credentials securely
