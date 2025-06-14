# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""OpenAI API client wrapper with tool integration."""

import os
import json
import openai
from openai.types.responses import FunctionToolParam, ResponseFunctionToolCallParam, ResponseInputParam
from openai.types.responses.response_input_param import FunctionCallOutput
from typing import override

from ..tools.base import Tool, ToolCall, ToolResult
from ..utils.config import ModelParameters
from .base_client import LLMUsage, LLMMessage, LLMResponse, BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI client wrapper with tool schema generation."""
    
    def __init__(self, model_parameters: ModelParameters):
        super().__init__(model_parameters)
        
        if self.api_key == "":
            self.api_key: str = os.getenv("OPENAI_API_KEY", "")
        
        if self.api_key == "":
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY in environment variables or config file.")
        
        self.client: openai.OpenAI = openai.OpenAI(api_key=self.api_key)
        self.message_history: ResponseInputParam = []
    
    @override
    def set_chat_history(self, messages: list[LLMMessage]) -> None:
        """Set the chat history."""
        self.message_history = self.parse_messages(messages)
    
    @override
    def chat(self, messages: list[LLMMessage], model_parameters: ModelParameters, tools: list[Tool] | None = None, reuse_history: bool = True) -> LLMResponse:
        """Send chat messages to OpenAI with optional tool support."""
        openai_messages: ResponseInputParam = self.parse_messages(messages)
        
        tool_schemas = None
        if tools:
            tool_schemas = [FunctionToolParam(
                name=tool.name,
                description=tool.description,
                parameters=tool.get_input_schema(),
                strict=True,
                type="function"
            ) for tool in tools]

        if reuse_history:
            self.message_history = self.message_history + openai_messages
        else:
            self.message_history = openai_messages

        response = self.client.responses.create(
            input=self.message_history,
            model=model_parameters.model,
            tools=tool_schemas if tool_schemas else openai.NOT_GIVEN,
            temperature=model_parameters.temperature,
            top_p=model_parameters.top_p,
            max_output_tokens=model_parameters.max_tokens,
        )

        content = ""
        tool_calls: list[ToolCall] = []
        for output_block in response.output:
            if output_block.type == "function_call":
                tool_calls.append(ToolCall(
                    call_id=output_block.call_id,
                    name=output_block.name,
                    arguments=json.loads(output_block.arguments),
                    id=output_block.id
                ))
                tool_call_param = ResponseFunctionToolCallParam(
                    arguments=output_block.arguments,
                    call_id=output_block.call_id,
                    name=output_block.name,
                    type="function_call",
                )
                if output_block.status:
                    tool_call_param["status"] = output_block.status
                if output_block.id:
                    tool_call_param["id"] = output_block.id
                self.message_history.append(tool_call_param)
            elif output_block.type == "message":
                for content_block in output_block.content:
                    if content_block.type == "output_text":
                        content += content_block.text
        
        usage = None
        if response.usage:
            usage = LLMUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                cache_read_input_tokens=response.usage.input_tokens_details.cached_tokens,
                reasoning_tokens=response.usage.output_tokens_details.reasoning_tokens
            )

        llm_response = LLMResponse(
            content=content,
            usage=usage,
            model=response.model,
            finish_reason=response.status,
            tool_calls=tool_calls if len(tool_calls) > 0 else None
        )
        
        # Record trajectory if recorder is available
        if self.trajectory_recorder:
            self.trajectory_recorder.record_llm_interaction(
                messages=messages,
                response=llm_response,
                provider="openai",
                model=model_parameters.model,
                tools=tools
            )
        
        return llm_response
    
    @override
    def supports_tool_calling(self, model_parameters: ModelParameters) -> bool:
        """Check if the current model supports tool calling."""

        if 'o1-mini' in model_parameters.model:
            return False

        tool_capable_models = [
            "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
            "gpt-4.1", "gpt-4.5",
            "o1", "o3", "o4"
        ]
        return any(model in model_parameters.model for model in tool_capable_models)

    def parse_messages(self, messages: list[LLMMessage]) -> ResponseInputParam:
        """Parse the messages to OpenAI format."""
        openai_messages: ResponseInputParam = []
        for msg in messages:
            if msg.tool_result:
                openai_messages.append(self.parse_tool_call_result(msg.tool_result))
            elif msg.tool_call:
                openai_messages.append(self.parse_tool_call(msg.tool_call))
            else:
                if not msg.content:
                    raise ValueError("Message content is required")
                if msg.role == "system":
                    openai_messages.append({"role": "system", "content": msg.content})
                elif msg.role == "user":
                    openai_messages.append({"role": "user", "content": msg.content})
                elif msg.role == "assistant":
                    openai_messages.append({"role": "assistant", "content": msg.content})
                else:
                    raise ValueError(f"Invalid message role: {msg.role}")
        return openai_messages

    def parse_tool_call(self, tool_call: ToolCall) -> ResponseFunctionToolCallParam:
        """Parse the tool call from the LLM response."""
        return ResponseFunctionToolCallParam(
            call_id=tool_call.call_id,
            name=tool_call.name,
            arguments=json.dumps(tool_call.arguments),
            type="function_call",
        )

    def parse_tool_call_result(self, tool_call_result: ToolResult) -> FunctionCallOutput:
        """Parse the tool call result from the LLM response."""
        result: str = ""
        if tool_call_result.result:
            result = result + tool_call_result.result + "\n"
        if tool_call_result.error:
            result += tool_call_result.error
        result = result.strip()
        
        return FunctionCallOutput(
            call_id=tool_call_result.call_id,
            id=tool_call_result.id,
            output=result,
            type="function_call_output",
        )