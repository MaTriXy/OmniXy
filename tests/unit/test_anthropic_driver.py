"""Unit tests for the Anthropic driver."""

from unittest.mock import patch, MagicMock

from src.core.request import MCPRequest, Message
from src.core.response import MCPResponse, MCPPartialResponse
from src.drivers.anthropic_driver import AnthropicDriver, AnthropicParameters


class TestAnthropicDriver:
    """Test suite for the Anthropic driver."""

    def test_init(self):
        """Test driver initialization."""
        # Test with default config
        driver = AnthropicDriver()
        assert driver.test_mode is False
        assert driver.mock_responses is False

        # Test with test mode config
        driver = AnthropicDriver({"test_mode": True})
        assert driver.test_mode is True

        # Test with mock responses config
        driver = AnthropicDriver({"mock_responses": True})
        assert driver.mock_responses is True

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Test with valid parameters
        params = AnthropicParameters(
            temperature=0.7, max_tokens=100, top_p=0.9, top_k=40
        )
        assert params.temperature == 0.7
        assert params.max_tokens == 100
        assert params.top_p == 0.9
        assert params.top_k == 40

        # Test with partial parameters
        params = AnthropicParameters(temperature=0.7)
        assert params.temperature == 0.7
        assert params.max_tokens is None

    def test_mock_response(self):
        """Test mock response generation."""
        driver = AnthropicDriver({"mock_responses": True})
        request = MCPRequest(
            model="claude-3.7-sonnet",
            messages=[Message(role="user", content="Hello, world!")],
        )

        response = driver.send_request(request)
        assert isinstance(response, MCPResponse)
        assert "mock response from Anthropic" in response.text
        assert response.model == "claude-3.7-sonnet"  # Match the model name used in the request
        assert response.finish_reason == "stop"
        assert "total_tokens" in response.usage

    def test_mock_streaming(self):
        """Test mock streaming response."""
        driver = AnthropicDriver({"mock_responses": True})
        request = MCPRequest(
            model="claude-3.7-sonnet",
            messages=[Message(role="user", content="Hello, world!")],
            stream=True,
        )

        stream = list(driver.stream_tokens(request))
        assert len(stream) > 0
        assert all(isinstance(chunk, MCPPartialResponse) for chunk in stream)
        full_text = "".join(chunk.partial_text for chunk in stream)
        assert "mock streaming response" in full_text

    @patch("anthropic.Anthropic")
    def test_send_request(self, mock_anthropic):
        """Test sending a request to the Anthropic API."""
        # Setup mock response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.model = "claude-3.7-sonnet"
        mock_response.stop_reason = "stop"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_response.id = "test-id"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_client.messages.create.return_value = mock_response

        # Create driver and request
        driver = AnthropicDriver({"api_key": "test-key"})
        request = MCPRequest(
            model="claude-3.7-sonnet",
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello, world!"),
            ],
            parameters={"temperature": 0.7, "max_tokens": 100},
        )

        # Send request
        response = driver.send_request(request)

        # Verify response
        assert response.text == "Test response"
        assert response.model == "claude-3.7-sonnet"
        assert response.finish_reason == "stop"
        assert response.usage["total_tokens"] == 30
        assert response.metadata["id"] == "test-id"

        # Verify API call
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "claude-3.7-sonnet"
        assert call_args["system"] == "You are a helpful assistant."
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "Hello, world!"
        assert call_args["temperature"] == 0.7
        assert "max_tokens_to_sample" in call_args
        assert call_args["max_tokens_to_sample"] == 100

    @patch("anthropic.Anthropic")
    def test_stream_tokens(self, mock_anthropic):
        """Test streaming tokens from the Anthropic API."""
        # Setup mock stream
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_stream = MagicMock()
        mock_stream.response_id = "test-stream-id"

        # Create mock chunks
        chunk1 = MagicMock()
        chunk1.type = "content_block_delta"
        chunk1.delta.text = "Hello"

        chunk2 = MagicMock()
        chunk2.type = "content_block_delta"
        chunk2.delta.text = ", world!"

        # Setup the stream context manager
        mock_client.messages.stream.return_value.__enter__.return_value = mock_stream
        mock_stream.__iter__.return_value = [chunk1, chunk2]

        # Create driver and request
        driver = AnthropicDriver({"api_key": "test-key"})
        request = MCPRequest(
            model="claude-3.7-sonnet",
            messages=[
                Message(role="system", content="You are a helpful assistant."),
                Message(role="user", content="Hello, world!"),
            ],
            stream=True,
            parameters={"temperature": 0.7, "max_tokens": 100},
        )

        # Stream tokens
        stream = list(driver.stream_tokens(request))

        # Verify stream
        assert len(stream) == 2
        assert stream[0].partial_text == "Hello"
        assert stream[1].partial_text == ", world!"
        assert all(chunk.metadata["id"] == "test-stream-id" for chunk in stream)

        # Verify API call
        mock_client.messages.stream.assert_called_once()
        call_args = mock_client.messages.stream.call_args[1]
        assert call_args["model"] == "claude-3.7-sonnet"
        assert call_args["system"] == "You are a helpful assistant."
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "Hello, world!"
        assert call_args["temperature"] == 0.7
        assert "max_tokens_to_sample" in call_args
        assert call_args["max_tokens_to_sample"] == 100
        assert call_args["stream"] is True
