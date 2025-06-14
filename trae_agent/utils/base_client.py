# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import override, Any
from pydantic import BaseModel
from abc import ABC, abstractmethod
from ..tools.base import Tool, ToolCall, ToolResult
from ..utils.config import ModelParameters


class ToolMessage(BaseModel):
    """Tool message format."""

class LLMMessage(BaseModel):
    """Standard message format."""
    role: str
    content: str | None = None
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None


class LLMUsage(BaseModel):
    """LLM usage format."""
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    reasoning_tokens: int = 0

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        return LLMUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens
        )

    @override
    def __str__(self) -> str:
        return f"LLMUsage(input_tokens={self.input_tokens}, output_tokens={self.output_tokens}, cache_creation_input_tokens={self.cache_creation_input_tokens}, cache_read_input_tokens={self.cache_read_input_tokens}, reasoning_tokens={self.reasoning_tokens})"


class LLMResponse(BaseModel):
    """Standard LLM response format."""
    content: str
    usage: LLMUsage | None = None
    model: str | None = None
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None


class BaseLLMClient(ABC):
    """Base class for LLM clients."""
    
    def __init__(self, model_parameters: ModelParameters):
        self.api_key: str = model_parameters.api_key
        self.trajectory_recorder: Any | None = None  # TrajectoryRecorder instance
    
    def set_trajectory_recorder(self, recorder: Any | None) -> None:
        """Set the trajectory recorder for this client."""
        self.trajectory_recorder = recorder

    @abstractmethod
    def set_chat_history(self, messages: list[LLMMessage]) -> None:
        """Set the chat history."""
        pass

    @abstractmethod
    def chat(self, messages: list[LLMMessage], model_parameters: ModelParameters, tools: list[Tool] | None = None, reuse_history: bool = True) -> LLMResponse:
        """Send chat messages to the LLM."""
        pass

    @abstractmethod
    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current model supports tool calling."""
        pass
    