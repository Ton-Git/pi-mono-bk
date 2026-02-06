"""Anthropic-compatible API models."""

from pydantic import BaseModel, Field
from typing import Optional, Union, List, Any, Literal


class TextContentBlock(BaseModel):
    """Text content block."""
    type: Literal["text"] = "text"
    text: str


class ImageContentBlock(BaseModel):
    """Image content block."""
    type: Literal["image"] = "image"
    source: dict


class ToolUseContentBlock(BaseModel):
    """Tool use content block."""
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: dict[str, Any]


class ToolResultContentBlock(BaseModel):
    """Tool result content block."""
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str
    is_error: bool = False


ContentBlock = Union[
    TextContentBlock,
    ImageContentBlock,
    ToolUseContentBlock,
    ToolResultContentBlock,
]


class MessageRole(str):
    """Message role."""
    user = "user"
    assistant = "assistant"


class AnthropicMessage(BaseModel):
    """Message in the conversation."""
    role: Literal["user", "assistant"]
    content: Union[str, List[ContentBlock]]


class ToolDefinition(BaseModel):
    """Tool definition."""
    name: str
    description: Optional[str] = None
    input_schema: dict[str, Any]


class MessageRequest(BaseModel):
    """Message creation request."""
    model: str
    max_tokens: int
    messages: List[AnthropicMessage]
    system: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    input_tokens: int
    output_tokens: int


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    content: List[ContentBlock]
    model: str
    stop_reason: Literal["end_turn", "max_tokens", "tool_use", "stop_sequence"]
    stop_sequence: Optional[str] = None
    usage: UsageInfo


class ModelObject(BaseModel):
    """Model object."""
    id: str
    name: str
    display_name: str
    type: Literal["model"] = "model"


class ModelsListResponse(BaseModel):
    """List of models response."""
    data: List[ModelObject]
    has_more: bool = False
