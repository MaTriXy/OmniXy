from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class Message(BaseModel):
    """A message in a conversation with an AI model."""

    role: str = Field(
        ...,
        description="The role of the message sender (e.g., 'user', 'assistant', 'system')",
    )
    content: str = Field(..., description="The content of the message")


class MCPRequest(BaseModel):
    """Model Context Protocol Request model for AI completions and non-LLM services."""

    provider: Optional[str] = Field(
        None,
        description="The provider to use for this request (e.g., 'openai', 'cohere', 'gemini', 'github')",
    )
    model: str = Field(
        ...,
        description="The model to use for this request or service identifier for non-LLM services",
    )
    messages: List[Message] = Field(
        default_factory=list, description="The conversation messages (for LLM services)"
    )
    temperature: Optional[float] = Field(
        None, description="The sampling temperature to use (for LLM services)"
    )
    max_tokens: Optional[int] = Field(
        None, description="The maximum number of tokens to generate (for LLM services)"
    )
    stream: bool = Field(False, description="Whether to stream the response")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters for the request"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata for the request, including non-LLM specific actions",
    )

    @validator("messages")
    def validate_messages(cls, v, values):
        """Validate that messages list is not empty for LLM providers.

        For non-LLM providers (like GitHub, Slack, etc.), empty messages are allowed.
        The determination is made based on model name or metadata.
        """
        # Get the model name
        model = values.get("model", "")
        metadata = values.get("metadata", {})

        # List of known non-LLM services that don't require messages
        non_llm_services = ["github", "slack", "jira"]

        # Check if this is a non-LLM service request
        is_non_llm = (
            model.lower() in non_llm_services
            or metadata.get("service_type") == "non_llm"
            or metadata.get("api_type") in non_llm_services
        )

        # Only validate non-empty messages for LLM services
        if not is_non_llm and not v:
            raise ValueError("Messages cannot be empty for LLM services")

        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create a model from a dictionary."""
        return cls(**data)

    def is_valid(self) -> bool:
        """Validate the request parameters."""
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False
