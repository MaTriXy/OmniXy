<!-- markdownlint-disable MD041 -->
<!-- markdownlint-disable MD033 -->
<div align="center" style="display: flex; align-items: center; justify-content: center;">
  <div>
    <img src="docs/logo.jpg" width="180" height="180" alt="OmniXy Logo" style="margin-left: 20px;" title="OmniXy logo - rendered by grok">
    <h1>OmniXy</h1>
    <h2>Universal Model Context Protocol (MCP) Client in python</h2>
  </div>
</div>
<!-- markdownlint-enable MD033 -->

OmniXy is a universal Model Context Protocol (MCP) client designed to enable seamless integration with any Large Language Model (LLM). It supports structured reasoning (chain-of-thought) and robust management of prompts, responses, and contexts according to the MCP specification.

## Key Features

- **Vendor-Agnostic**: Easily switch between or integrate multiple LLM backends.
- **Standards-Based**: Leverages the Model Context Protocol to ensure consistency in request/response structures.
- **Extensible**: New LLM providers can be added via a driver pattern without refactoring the core.
- **Reasoning-Capable**: Orchestrate multi-step chain-of-thought processing for complex tasks.
- **Secure & Scalable**: Incorporates best practices for authentication, concurrency, caching, and data handling.
- **Type-Safe**: Uses Pydantic for data validation, serialization, and documentation.

## Supported Models Names

For easier integration - our model name is structured as follows: `provider-model-name:version`.

as you can see in the models listed in the [Open Router model list](https://openrouter.ai/models), as of **February 25, 2025**. For the most up-to-date list of supported models, refer to our [open_router_models.json](docs/open_router_models.json) file.

## Getting Started

1. **Installation**:

    ```bash
    # Using uv (Python)
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    ```

2. **Configuration**:
    - Set up your LLM provider credentials (e.g., Anthropic API key) in a secure vault or environment variables.

3. **Usage Examples**:

### Basic Completion

```python
    from universal_mcp_client import MCPClient

    client = MCPClient(provider="anthropic", api_key="YOUR_API_KEY")
    response = client.complete(
        messages=[{"role": "user", "content": "Explain quantum entanglement"}],
        model="claude-3.7-sonnet",
        stream=True
    )

    for chunk in response:
        print(chunk)
    ```

    ### Chain of Thought Reasoning

    ```python
    # Multi-step reasoning for complex tasks
    from universal_mcp_client import MCPClient, ChainOfThought

    client = MCPClient(provider="anthropic")
    chain = ChainOfThought(client)
    
    result = chain.solve([
        {"task": "Research phase", "prompt": "Analyze the given data"}, 
        {"task": "Planning", "prompt": "Create an action plan"}, 
        {"task": "Execution", "prompt": "Implement the solution"}
    ])
    ```

    ### Multiple Provider Integration

    ```python
    # Using multiple LLM providers in parallel
    from universal_mcp_client import MCPClient

    anthropic_client = MCPClient(provider="anthropic")
    cohere_client = MCPClient(provider="cohere")
    local_client = MCPClient(provider="local", model_path="/path/to/model")

    # Run inference across different providers
    responses = await asyncio.gather(
        anthropic_client.complete_async(messages=[{"role": "user", "content": prompt}]),
        cohere_client.complete_async(messages=[{"role": "user", "content": prompt}]),
        local_client.complete_async(messages=[{"role": "user", "content": prompt}])
    )
    ```

    ### Custom Provider Configuration

    ```python
    # Configure provider-specific parameters
    client = MCPClient(
        provider="anthropic",
        config={
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.95,
            "cache_enabled": True,
            "retry_strategy": "exponential",
            "timeout": 30
        }
    )
    ```

    ### Error Handling

    ```python
    from universal_mcp_client import MCPClient, MCPError

    client = MCPClient(provider="anthropic")
    
    try:
        response = client.complete(
            messages=[{"role": "user", "content": "Generate a story"}],
            model="claude-3.7-sonnet"
        )
    except MCPError as e:
        if e.error_type == "RateLimitError":
            print("Rate limit exceeded, retrying after cooldown")
        elif e.error_type == "AuthenticationError":
            print("Please check your API credentials")
        else:
            print(f"An error occurred: {e}")
    ```

### Using Pydantic Models

OmniXy uses Pydantic throughout the codebase for data validation, serialization, and documentation. You can leverage these models in your own code:

```python
from src.core.request import MCPRequest, Message
from src.core.response import MCPResponse
from src.core.settings import Settings, get_settings

# Create a request using Pydantic models
request = MCPRequest(
    provider="anthropic",
    model="claude-3.7-sonnet",
    messages=[
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Tell me about quantum computing.")
    ]
)

# Access settings with type hints and validation
settings = get_settings()
print(f"Using default model: {settings.default_models['anthropic']}")

# Create your own models that extend OmniXy's models
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class CustomCompletionRequest(BaseModel):
    request: MCPRequest
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tracking_id: Optional[str] = None
```

### Environment Variables and Settings

OmniXy uses Pydantic's `BaseSettings` to manage configuration through environment variables:

1. Copy the `.env.example` file to `.env` and fill in your API keys:

    ```bash
    cp .env.example .env
    # Edit .env with your API keys and settings
    ```

2. Settings are automatically loaded from the `.env` file:

```python
from src.core.settings import get_settings

settings = get_settings()

# Access API keys and other settings
anthropic_api_key = settings.api.anthropic_api_key.get_secret_value()
default_timeout = settings.server.default_timeout
```

### Schema Generation

OmniXy includes a schema generator that creates OpenAPI/JSON Schema documentation for all Pydantic models:

```python
from src.core.schema_generator import generate_all_schemas
from pathlib import Path

# Generate schemas for all models
output_dir = Path("docs/schemas")
schemas = generate_all_schemas(output_dir)
```

## Project Structure

```text
OmniXy/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── mcp_protocol.md
│   ├── provider_drivers.md
│   ├── orchestration.md
│   ├── security.md
├── src/
│   ├── __init__.py
│   ├── client.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── mcp_layer.py
│   │   ├── request.py
│   │   ├── response.py
│   │   ├── settings.py
│   │   ├── schema_generator.py
│   ├── drivers/
│   │   ├── __init__.py
│   │   ├── driver_factory.py
│   │   ├── anthropic_driver.py
│   │   ├── openai_driver.py
│   │   ├── cohere_driver.py
│   │   ├── gemini_driver.py
│   │   ├── local_llm_driver.py
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── chain_of_thought.py
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── workflow_manager.py
│   ├── plugin/
│   │   ├── __init__.py
│   │   ├── plugin_manager.py
├── tests/
│   ├── unit/
│   ├── integration/
```

## Testing

OmniXy maintains a comprehensive test suite with both unit and integration tests.
We strive for 80% or higher code coverage.

### Running Tests

```bash
# Install test dependencies
uv pip install pytest pytest-cov pytest-asyncio

# Run all tests
uv pip run pytest

# Run only unit tests
uv pip run pytest tests/unit

# Run only integration tests
uv pip run pytest tests/integration

# Run with coverage report
uv pip run pytest --cov=src tests/ --cov-report=term-missing --cov-report=xml
```

### Test Structure

- **Unit Tests**: Located in `tests/unit/`
  - `test_mcp_layer.py`: Tests for core MCP protocol functionality
  - `test_request.py`: Request handling and validation
  - `test_response.py`: Response processing and formatting
  - `test_workflow_manager.py`: Workflow creation and execution
  - `test_plugin_manager.py`: Plugin system functionality
  - `test_chain_of_thought.py`: Chain-of-thought orchestration

- **Integration Tests**: Located in `tests/integration/`
  - `test_workflow_plugin_integration.py`: Workflow and plugin interaction
  - `test_mcp_providers.py`: Provider-specific integration tests

### Writing Tests

When contributing new features:

1. Add corresponding unit tests in `tests/unit/`
2. Add integration tests if the feature interacts with other components
3. Ensure tests are properly documented
4. Verify test coverage remains at or above 80%

## Contributing

### Development Setup

1. Fork and clone the repository
2. Set up the development environment:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Install development dependencies
uv pip install pytest pytest-cov pytest-asyncio ruff black mypy
```

### Development Workflow

1. Create a new branch for your feature:

    ```bash
    git checkout -b feature/your-feature-name
    ```

2. Make your changes and ensure all tests pass:

    ```bash
    # Run tests
    uv pip run pytest

    # Run linters
    ruff check .
    black .
    mypy src tests
    ```

3. Commit your changes using conventional commits:

    ```bash
    git commit -m "feat: add new feature"
    ```

4. Push your branch and create a Pull Request

### Continuous Integration

When you open a Pull Request targeting the main branch, our CI workflow will automatically:

1. Run tests on multiple Python versions (3.9, 3.10, 3.11)
2. Generate and upload test coverage reports
3. Run linting checks (ruff, black, mypy)
4. Verify documentation updates

Ensure all CI checks pass before requesting a review.

## License

For commercial use, please contact the Licensor via [LinkedIn](https://www.linkedin.com/in/yossielkrief) or via X [@elkriefy](https://x.com/elkriefy).

For more information: [LICENSE](LICENSE)
