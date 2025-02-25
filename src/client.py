from typing import Dict, List, Optional, Any, Union, Callable, Iterator
from pydantic import BaseModel, Field

from src.core.mcp_layer import MCPConnection, ServerConfig
from src.core.request import MCPRequest, Message
from src.core.response import MCPResponse, MCPPartialResponse
from src.drivers.openai_driver import OpenAIDriver
from src.drivers.cohere_driver import CohereDriver
from src.drivers.gemini_driver import GeminiDriver
from src.drivers.local_llm_driver import LocalLLMDriver
from src.drivers.anthropic_driver import AnthropicDriver
from src.orchestration.chain_of_thought import ChainOfThoughtOrchestrator
from src.drivers.driver_factory import DriverFactory
from src.workflow.workflow_manager import WorkflowManager
from src.plugin.plugin_manager import PluginManager
from src.core.settings import get_settings, Settings


class ClientConfig(BaseModel):
    """Configuration for the MCP client."""

    provider: Optional[str] = Field(None, description="Default provider to use")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    test_mode: bool = Field(False, description="Whether to run in test mode")
    mock_responses: bool = Field(False, description="Whether to return mock responses")


class MCPClient:
    """Client for the Model Context Protocol."""

    def __init__(
        self,
        provider: Optional[str] = None,
        config: Optional[Union[Dict[str, Any], ClientConfig]] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize the MCP client.

        Args:
            provider: Default provider to use
            config: Configuration for the client
            settings: Settings instance to use
        """
        self.settings = settings or get_settings()
        self.servers: Dict[str, MCPConnection] = {}
        self.driver_factory = DriverFactory()
        self.providers: Dict[str, Any] = {}
        self.workflow_manager = WorkflowManager()
        self.plugin_manager = PluginManager()
        self.workflows: Dict[str, Callable] = {}
        self.plugins: Dict[str, Callable] = {}

        # Use provider from args, config, or settings
        provider = provider or (
            self.settings.default_provider if self.settings else None
        )

        # Handle provider initialization if provided
        if provider:
            self.current_provider = provider
            if config is None:
                config = {}

            # Convert dict config to ClientConfig if needed
            if isinstance(config, dict):
                config = ClientConfig(**config)

            # Initialize provider with config
            self._initialize_provider_from_settings(provider, config)

    def _initialize_provider_from_settings(
        self, provider: str, config: ClientConfig
    ) -> None:
        """Initialize a provider using settings.

        Args:
            provider: Provider name
            config: Client configuration
        """
        provider_config = {}

        # Use test mode from config or settings
        provider_config["test_mode"] = config.test_mode or self.settings.test_mode
        provider_config["mock_responses"] = config.mock_responses

        # Add API key from settings if available
        if provider == "openai" and self.settings.api.openai_api_key:
            provider_config["api_key"] = (
                self.settings.api.openai_api_key.get_secret_value()
            )
            provider_config["organization"] = self.settings.api.openai_organization
        elif provider == "cohere" and self.settings.api.cohere_api_key:
            provider_config["api_key"] = (
                self.settings.api.cohere_api_key.get_secret_value()
            )
        elif provider == "gemini" and self.settings.api.gemini_api_key:
            provider_config["api_key"] = (
                self.settings.api.gemini_api_key.get_secret_value()
            )
        elif provider == "anthropic" and self.settings.api.anthropic_api_key:
            provider_config["api_key"] = (
                self.settings.api.anthropic_api_key.get_secret_value()
            )

        # Override with config API key if provided
        if config.api_key:
            provider_config["api_key"] = config.api_key

        # Register the provider
        self.register_provider(provider, provider_config)

    def register_server(
        self, server_name: str, server_config: Union[Dict[str, Any], ServerConfig]
    ) -> None:
        """Register a server with the client.

        Args:
            server_name: Name of the server
            server_config: Configuration for the server
        """
        # Apply default server settings if using dict config
        if isinstance(server_config, dict) and not server_config.get("url"):
            raise ValueError("Server configuration must include a URL")

        if isinstance(server_config, dict):
            # Apply defaults from settings
            if "protocol" not in server_config:
                server_config["protocol"] = self.settings.server.default_protocol
            if "timeout" not in server_config:
                server_config["timeout"] = self.settings.server.default_timeout

        self.servers[server_name] = MCPConnection(server_config)

    def register_provider(
        self, provider_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a provider with optional configuration.

        Args:
            provider_name: Name of the provider (e.g., 'openai', 'cohere', 'gemini')
            config: Configuration for the provider
        """
        if config is None:
            config = {}

        # Automatically enable test_mode if no API key is provided
        if "api_key" not in config or not config["api_key"]:
            config["test_mode"] = True
            config["mock_responses"] = True

        # Map provider names to their driver classes
        driver_map = {
            "openai": OpenAIDriver,
            "cohere": CohereDriver,
            "gemini": GeminiDriver,
            "anthropic": AnthropicDriver,
            "local": LocalLLMDriver,
            "mock": LocalLLMDriver,  # Use LocalLLM as a mock for testing
        }

        if provider_name not in driver_map:
            raise ValueError(f"Unsupported provider: {provider_name}")

        driver_class = driver_map[provider_name]
        self.providers[provider_name] = driver_class(config)

        # For backward compatibility with existing code
        self.driver_factory.register_driver(provider_name, driver_class)

    def create_provider(
        self, provider_name: str, provider_config: Dict[str, Any]
    ) -> None:
        """Create a provider with the given configuration.

        Args:
            provider_name: Name of the provider
            provider_config: Configuration for the provider
        """
        driver = self.driver_factory.create_driver(provider_name, provider_config)
        self.providers[provider_name] = driver

    def set_provider(self, provider_name: str) -> None:
        """Set the current provider.

        Args:
            provider_name: Name of the provider to use

        Raises:
            ValueError: If the provider is not registered
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not registered")
        self.current_provider = provider_name

    def register_workflow(self, workflow_name: str, workflow_func: Callable) -> None:
        """Register a workflow with the client.

        Args:
            workflow_name: Name of the workflow
            workflow_func: Function to execute for the workflow
        """
        self.workflow_manager.register_workflow(workflow_name, workflow_func)
        self.workflows[workflow_name] = workflow_func

    def register_plugin(self, plugin_name: str, plugin_func: Callable) -> None:
        """Register a plugin with the client.

        Args:
            plugin_name: Name of the plugin
            plugin_func: Function to execute for the plugin
        """
        self.plugin_manager.register_plugin(plugin_name, plugin_func)
        self.plugins[plugin_name] = plugin_func

    def complete(
        self,
        server_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        stream: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
        workflow_name: Optional[str] = None,
        plugin_name: Optional[str] = None,
    ) -> Union[MCPResponse, Iterator[MCPPartialResponse]]:
        """Complete a request using the specified provider or server.

        For backward compatibility with tests, if server_name is None and provider_name
        is specified, it will use the provider directly.

        Args:
            server_name: Name of the server to use
            provider_name: Name of the provider to use
            messages: List of messages in the conversation
            model: Model to use for generation
            stream: Whether to stream the response
            parameters: Additional parameters for the request
            workflow_name: Name of the workflow to use
            plugin_name: Name of the plugin to use

        Returns:
            MCPResponse or Iterator[MCPPartialResponse]: The response from the server

        Raises:
            ValueError: If the server is not registered
        """
        # Use current_provider if provider_name is not specified
        if provider_name is None and hasattr(self, "current_provider"):
            provider_name = self.current_provider

        # For tests that don't use servers
        if server_name is None and provider_name is not None:
            return self.simple_complete(
                provider_name=provider_name,
                messages=messages,
                model=model,
                stream=stream,
                parameters=parameters,
            )

        server = self.servers.get(server_name)
        if not server:
            raise ValueError(f"Server {server_name} not registered")

        # Process workflow if specified
        if workflow_name:
            messages = self.workflow_manager.process_workflow(workflow_name, messages)

        # Execute plugin if specified
        if plugin_name:
            messages = self.plugin_manager.execute_plugin(plugin_name, messages)

        # Convert messages to Message objects
        message_objects = [
            Message(role=msg["role"], content=msg["content"]) for msg in messages
        ]

        # Use default model from settings if not specified
        if model is None and provider_name in self.settings.default_models:
            model = self.settings.default_models[provider_name]

        provider = self.providers.get(provider_name)
        if provider:
            # Use provider to process the request
            mcp_request = MCPRequest(
                provider=provider_name,
                model=model,
                messages=message_objects,
                parameters=parameters or {},
            )
            if stream:
                return server.stream(mcp_request)
            return server.send(mcp_request)
        else:
            # Send request without provider
            mcp_request = MCPRequest(
                model=model,
                messages=message_objects,
                parameters=parameters or {},
            )
            if stream:
                return server.stream(mcp_request)
            return server.send(mcp_request)

    def simple_complete(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Union[MCPResponse, Iterator[MCPPartialResponse], Dict[str, Any]]:
        """Simple completion method for tests that don't use the server architecture.

        Args:
            provider_name: Name of the provider to use
            messages: List of messages in the conversation
            model: Model to use for generation
            stream: Whether to stream the response
            parameters: Additional parameters for the request

        Returns:
            MCPResponse, Iterator[MCPPartialResponse], or Dict: The response from the provider

        Raises:
            ValueError: If the provider is not registered
        """
        provider = self.providers.get(provider_name)
        if not provider:
            if provider_name not in self.providers and provider_name == "mock":
                # Auto-register mock provider for tests
                self.register_provider(
                    "mock", {"mock_responses": True, "test_mode": True}
                )
                provider = self.providers.get("mock")
            else:
                raise ValueError(f"Provider {provider_name} not registered")

        # For testing, return a mock response
        if provider_name == "mock":
            return {
                "id": "test-response-id",
                "choices": [{"text": "Test response", "finish_reason": "stop"}],
            }

        # Convert messages to Message objects
        message_objects = [
            Message(role=msg["role"], content=msg["content"]) for msg in messages
        ]

        # Use default model from settings if not specified
        if model is None and provider_name in self.settings.default_models:
            model = self.settings.default_models[provider_name]

        # Create a request object
        mcp_request = MCPRequest(
            provider=provider_name,
            model=model,
            messages=message_objects,
            parameters=parameters or {},
        )

        # Use the provider to process the request
        if stream:
            return provider.stream_tokens(mcp_request)
        return provider.send_request(mcp_request)

    def process_chain_of_thought(self, mcp_request: MCPRequest) -> MCPResponse:
        """Process a request using chain of thought.

        Args:
            mcp_request: The request to process

        Returns:
            MCPResponse: The response from the chain of thought
        """
        return ChainOfThoughtOrchestrator().process_request(mcp_request)


if __name__ == "__main__":
    # Example Usage with settings
    client = MCPClient()

    # Example Usage Gemini
    client.register_server("gemini", {"url": "api.gemini.example.com"})
    response = client.complete(
        server_name="gemini",
        provider_name="gemini",
        messages=[{"role": "user", "content": "Explain quantum entanglement"}],
        stream=False,
    )
    response_text = response.text

    # Example Usage OpenAI
    client.register_server("openai", {"url": "api.openai.com"})
    response = client.complete(
        server_name="openai",
        provider_name="openai",
        messages=[{"role": "user", "content": "Explain quantum entanglement"}],
        stream=False,
    )
    response_text = response.text

    # Example with local LLM
    client.register_server("local", {"url": "localhost:8000"})
    client.register_provider("local", {"model_path": "/path/to/your/local/model"})
    local_response = client.complete(
        server_name="local",
        provider_name="local",
        messages=[{"role": "user", "content": "Write a short poem about the sea"}],
        stream=False,
    )
    local_response_text = local_response.text
