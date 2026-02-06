"""OpenAI-compatible API models."""

from pydantic import BaseModel, Field
from typing import Optional, Union, List, Any, Literal
from enum import Enum


class ChatMessageRole(str, Enum):
    """Chat message role."""
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ChatMessage(BaseModel):
    """Chat message."""
    role: ChatMessageRole
    content: Optional[str] = None
    tool_calls: Optional[List["ChatMessageToolCall"]] = None
    tool_call_id: Optional[str] = None


class FunctionParameters(BaseModel):
    """Function parameters (JSON Schema)."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class ChatFunction(BaseModel):
    """Chat function definition."""
    name: str
    description: Optional[str] = None
    parameters: Optional[FunctionParameters] = None


class ChatTool(BaseModel):
    """Chat tool definition."""
    type: Literal["function"] = "function"
    function: ChatFunction


class ChatMessageToolCall(BaseModel):
    """Tool call in a message."""
    id: str
    type: Literal["function"] = "function"
    function: ChatFunction


class ChatCompletionRequest(BaseModel):
    """Chat completion request."""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[List[ChatTool]] = None
    tool_choice: Optional[Union[Literal["auto", "none", "required"], dict]] = None


class UsageInfo(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponseChoice(BaseModel):
    """Choice in chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """Chat completion response."""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: UsageInfo


class ChatCompletionStreamDelta(BaseModel):
    """Delta in streaming chat completion."""
    content: Optional[str] = None
    role: Optional[str] = None


class ChatCompletionStreamChoice(BaseModel):
    """Choice in streaming chat completion."""
    index: int
    delta: ChatCompletionStreamDelta
    finish_reason: Optional[str] = None


class ChatCompletionStreamResponse(BaseModel):
    """Streaming chat completion response chunk."""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionStreamChoice]


class ModelObject(BaseModel):
    """Model object."""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str


class ModelsListResponse(BaseModel):
    """List of models response."""
    object: Literal["list"] = "list"
    data: List[ModelObject]
