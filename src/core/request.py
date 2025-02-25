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
    """Model Context Protocol Request model for AI completions."""

    provider: Optional[str] = Field(
        None,
        description="The provider to use for this request (e.g., 'openai', 'cohere', 'gemini')",
    )
    model: str = Field(..., description="The model to use for this request")
    messages: List[Message] = Field(..., description="The conversation messages")
    temperature: Optional[float] = Field(
        None, description="The sampling temperature to use"
    )
    max_tokens: Optional[int] = Field(
        None, description="The maximum number of tokens to generate"
    )
    stream: bool = Field(False, description="Whether to stream the response")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Additional parameters for the request"
    )

    @validator("messages")
    def validate_messages(cls, v):
        """Validate that messages list is not empty."""
        if not v:
            raise ValueError("Messages cannot be empty")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create a model from a dictionary."""
        return cls(**data)

    def validate(self) -> bool:
        """Validate the request parameters."""
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False
