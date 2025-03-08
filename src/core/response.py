from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, validator


class MCPResponse(BaseModel):
    """Model Context Protocol Response model for AI completions and non-LLM service responses."""

    text: str = Field(..., description="The generated text response")
    usage: Dict[str, Any] = Field(
        default_factory=dict, description="Usage information such as token counts (for LLM services)"
    )
    model: Optional[str] = Field(None, description="The model used for generation")
    finish_reason: Optional[str] = Field(
        None, description="The reason why the generation finished"
    )
    is_chunk: bool = Field(
        False, description="Whether this is a chunk of a streaming response"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the response"
    )
    plugin_data: Dict[str, Any] = Field(
        default_factory=dict, description="Data from non-LLM services in structured format"
    )

    @validator("text")
    def validate_text(cls, v):
        """Validate that text is not empty."""
        if not v:
            raise ValueError("Text cannot be empty")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPResponse":
        """Create a model from a dictionary."""
        return cls(**data)

    def validate(self) -> bool:
        """Validate the response parameters."""
        try:
            self.model_validate(self.model_dump())
            return True
        except Exception:
            return False


class MCPPartialResponse(BaseModel):
    """Model Context Protocol Partial Response model for streaming responses."""

    partial_text: str = Field(
        ..., description="The partial text chunk in a streaming response"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the partial response",
    )
    is_final: bool = Field(
        False, description="Whether this is the final chunk in a streaming response"
    )
    plugin_data: Dict[str, Any] = Field(
        default_factory=dict, description="Data from non-LLM services in structured format"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPPartialResponse":
        """Create a model from a dictionary."""
        return cls(**data)
