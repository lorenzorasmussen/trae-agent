# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Base Agent class for LLM-based agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

from trae_agent.utils.config import ModelParameters

from ..utils.llm_client import LLMClient, LLMProvider
from ..utils.base_client import LLMResponse, LLMUsage, LLMMessage
from ..tools.base import Tool, ToolCall, ToolExecutor, ToolResult


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    CALLING_TOOL = "calling_tool"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentStep:
    """Represents a single step in agent execution."""
    step_number: int
    state: AgentState
    thought: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_results: list[ToolResult] | None = None
    llm_response: LLMResponse | None = None
    reflection: str | None = None
    error: str | None = None
    extra: dict[str, object] | None = None
    llm_usage: LLMUsage | None = None


@dataclass
class AgentExecution:
    """Represents a complete agent execution."""
    task: str
    steps: list[AgentStep]
    final_result: str | None = None
    success: bool = False
    total_tokens: LLMUsage | None = None
    execution_time: float = 0.0


class AgentError(Exception):
    """Base class for agent errors."""
    def __init__(self, message: str):
        self.message: str = message
        super().__init__(self.message)


class Agent(ABC):
    """Base class for LLM-based agents."""
    
    def __init__(self, llm_provider: LLMProvider, model_parameters: ModelParameters, max_steps: int = 10):
        self.llm_client: LLMClient = LLMClient(llm_provider, model_parameters)
        self.max_steps: int = max_steps
        self.model_parameters: ModelParameters = model_parameters
        self.initial_messages: list[LLMMessage] = []
        self.task: str = ""
        self.tools: list[Tool] = []
        self.tool_caller: ToolExecutor = ToolExecutor([])
        self.console: Console = Console()
        self.show_progress: bool = False
        self.progress_callback: Callable[[AgentStep], None] | None = None
        self.last_displayed_step_number: int | None = None
        self._live_display: Live | None = None
        self._current_step: AgentStep | None = None
        self._last_panel_height: int = 0
        self.trajectory_recorder: Any | None = None

    def set_trajectory_recorder(self, recorder: Any | None) -> None:
        """Set the trajectory recorder for this agent."""
        self.trajectory_recorder = recorder
        # Also set it on the LLM client
        self.llm_client.set_trajectory_recorder(recorder)

    def set_progress_display(self, show_progress: bool = True, progress_callback: Callable[[AgentStep], None] | None = None):
        """Configure progress display settings.
        
        Args:
            show_progress: Whether to show built-in progress display
            progress_callback: Optional callback function to handle custom progress display
        """
        self.show_progress = show_progress
        self.progress_callback = progress_callback

    def _create_step_display(self, step: AgentStep) -> Panel:
        """Create a panel for displaying the current step."""
        # Get state color and emoji
        state_info = {
            AgentState.THINKING: ("blue", "🤔"),
            AgentState.CALLING_TOOL: ("yellow", "🔧"),
            AgentState.REFLECTING: ("magenta", "💭"),
            AgentState.COMPLETED: ("green", "✅"),
            AgentState.ERROR: ("red", "❌"),
            AgentState.IDLE: ("white", "⏸️")
        }
        
        color, emoji = state_info.get(step.state, ("white", "❓"))
        
        # Build progressive step content
        step_content = []
        step_content.append(f"[{color}]{emoji} State: {step.state.value.title()}[/{color}]")
        
        # Show LLM response if available (truncated for readability)
        if step.llm_response and step.llm_response.content:
            step_content.append(f"\n[bold]💬 LLM Response:[/bold]\n{step.llm_response.content}")
        
        # Show tool calls
        if step.tool_calls:
            step_content.append(f"\n[bold]🔧 Tool Calls:[/bold]")
            for i, tool_call in enumerate(step.tool_calls):
                step_content.append(f"  {i+1}. [cyan]{tool_call.name}[/cyan]")
                if tool_call.arguments:
                    step_content.append(f"     Args: {tool_call.arguments}")
        
        # Show tool results
        if step.tool_calls and step.tool_results:
            step_content.append(f"\n[bold]📋 Tool Results:[/bold]")
            for i, result in enumerate(step.tool_results):
                status = "[green]✅ Success[/green]" if result.success else "[red]❌ Failed[/red]"
                step_content.append(f"  {i+1}. {status}")
                if result.error:
                    step_content.append(f"     [red]Error:[/red] {result.error}")
                elif result.result:
                    step_content.append(f"     [green]Output:[/green] {result.result}")
        
        # Show reflection
        if step.reflection:
            step_content.append(f"\n[bold]💭 Reflection:[/bold]\n{step.reflection}")
        
        # Show error
        if step.error:
            step_content.append(f"\n[red]❌ Error:[/red] {step.error}")
        
        return Panel(
            "\n".join(step_content),
            title=f"Step {step.step_number}",
            border_style=color,
            width=80
        )

    def display_step_progress(self, step: AgentStep):
        """Display progress for a single step, updating in place."""
        if not self.show_progress:
            return
        
        # Store current step for live updates
        self._current_step = step
        
        # Check if we're starting a new step
        if self.last_displayed_step_number != step.step_number:
            # Stop any existing live display
            if self._live_display:
                self._live_display.stop()
                self._live_display = None
            
            # Display task header only once at the beginning
            if self.last_displayed_step_number is None:
                self.console.print(Panel(
                    f"[bold]Task:[/bold] {self.task}",
                    title="🚀 Agent Execution",
                    border_style="blue"
                ))
            
            self.last_displayed_step_number = step.step_number
            
            # Start live display for this step
            step_panel = self._create_step_display(step)
            self._live_display = Live(step_panel, console=self.console, refresh_per_second=10)
            self._live_display.start()
        else:
            # Same step - update the live display
            if self._live_display:
                step_panel = self._create_step_display(step)
                self._live_display.update(step_panel)
            else:
                # Fallback if live display isn't working
                step_panel = self._create_step_display(step)
                self.console.print(step_panel)

    def display_execution_summary(self, execution: AgentExecution):
        """Display a summary of the agent execution."""
        if not self.show_progress:
            return
        
        # Create summary table
        table = Table(title="Execution Summary", width=60)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green", width=40)
        
        table.add_row("Task", execution.task[:50] + "..." if len(execution.task) > 50 else execution.task)
        table.add_row("Success", "✅ Yes" if execution.success else "❌ No")
        table.add_row("Steps", str(len(execution.steps)))
        table.add_row("Execution Time", f"{execution.execution_time:.2f}s")
        
        if execution.total_tokens:
            total_tokens = execution.total_tokens.input_tokens + execution.total_tokens.output_tokens
            table.add_row("Total Tokens", str(total_tokens))
            table.add_row("Input Tokens", str(execution.total_tokens.input_tokens))
            table.add_row("Output Tokens", str(execution.total_tokens.output_tokens))
        
        self.console.print(table)
        
        # Display final result
        if execution.final_result:
            self.console.print(Panel(
                execution.final_result,
                title="Final Result",
                border_style="green" if execution.success else "red"
            ))

    @abstractmethod
    def new_task(self, task: str, extra_args: dict[str, str] | None = None, tool_names: list[str] | None = None):
        """Create a new task."""
        pass
    
    async def execute_task(self) -> AgentExecution:
        """Execute a task using the agent."""
        import time
        start_time = time.time()
        
        execution = AgentExecution(task=self.task, steps=[])
        
        try:
            messages = self.initial_messages
            step_number = 1
            
            while step_number <= self.max_steps:
                step = AgentStep(step_number=step_number, state=AgentState.THINKING)
                
                try:
                    
                    # Get LLM response
                    step.state = AgentState.THINKING
                    
                    # Call progress callback if provided
                    if self.progress_callback:
                        self.progress_callback(step)
                    
                    # Display thinking state
                    if self.show_progress:
                        step_copy = AgentStep(step_number=step_number, state=AgentState.THINKING)
                        self.display_step_progress(step_copy)
                    
                    llm_response = self.llm_client.chat(messages, self.model_parameters, self.tools)
                    step.llm_response = llm_response
                    
                    # Display step with LLM response
                    if self.show_progress:
                        self.display_step_progress(step)
                    
                    # Update token usage
                    if llm_response.usage:
                        if execution.total_tokens:
                            execution.total_tokens += llm_response.usage
                        else:
                            execution.total_tokens = llm_response.usage

                    if self.llm_indicates_task_completed(llm_response):
                        if self.is_task_completed(llm_response):
                            step.state = AgentState.COMPLETED
                            execution.final_result = llm_response.content
                            execution.success = True
                            
                            # Display completion
                            if self.show_progress:
                                self.display_step_progress(step)
                            
                            # Call progress callback
                            if self.progress_callback:
                                self.progress_callback(step)
                            
                            # Record agent step
                            if self.trajectory_recorder:
                                self.trajectory_recorder.record_agent_step(
                                    step_number=step.step_number,
                                    state=step.state.value,
                                    llm_messages=messages,
                                    llm_response=step.llm_response,
                                    tool_calls=step.tool_calls,
                                    tool_results=step.tool_results,
                                    reflection=step.reflection,
                                    error=step.error
                                )
                            
                            execution.steps.append(step)
                            break
                        else:
                            step.state = AgentState.THINKING
                            messages = [LLMMessage(role="user", content=self.task_incomplete_message())]
                    else:
                        # Check if the response contains a tool call
                        tool_calls = llm_response.tool_calls

                        if tool_calls and len(tool_calls) > 0:
                            # Execute tool call
                            step.state = AgentState.CALLING_TOOL
                            step.tool_calls = tool_calls
                            
                            # Display tool calling state with tool calls
                            if self.show_progress:
                                self.display_step_progress(step)
                            
                            # Call progress callback
                            if self.progress_callback:
                                self.progress_callback(step)
                            
                            if self.model_parameters.parallel_tool_calls:
                                tool_results = await self.tool_caller.parallel_tool_call(tool_calls)
                            else:
                                tool_results = await self.tool_caller.sequential_tool_call(tool_calls)
                            step.tool_results = tool_results
                            
                            # Display tool results
                            if self.show_progress:
                                self.display_step_progress(step)
                            
                            messages: list[LLMMessage] = []
                            for tool_result in tool_results:
                                # Add tool result to conversation
                                message = LLMMessage(
                                    role="user",
                                    tool_result=tool_result
                                )
                                messages.append(message)

                            reflection = self.reflect_on_result(tool_results)
                            if reflection:
                                step.state = AgentState.REFLECTING
                                step.reflection = reflection
                                
                                # Display reflection
                                if self.show_progress:
                                    self.display_step_progress(step)
                                
                                # Call progress callback
                                if self.progress_callback:
                                    self.progress_callback(step)
                                
                                messages.append(LLMMessage(role="assistant", content=reflection))
                        else:
                            # No tool calls - LLM response already displayed above
                            # Call progress callback
                            if self.progress_callback:
                                self.progress_callback(step)
                        
                    # Record agent step
                    if self.trajectory_recorder:
                        self.trajectory_recorder.record_agent_step(
                            step_number=step.step_number,
                            state=step.state.value,
                            llm_messages=messages,
                            llm_response=step.llm_response,
                            tool_calls=step.tool_calls,
                            tool_results=step.tool_results,
                            reflection=step.reflection,
                            error=step.error
                        )
                    
                    execution.steps.append(step)
                    step_number += 1
                    
                except Exception as e:
                    step.state = AgentState.ERROR
                    step.error = str(e)
                    
                    # Display error
                    if self.show_progress:
                        self.display_step_progress(step)
                    
                    # Call progress callback
                    if self.progress_callback:
                        self.progress_callback(step)
                    
                    # Record agent step
                    if self.trajectory_recorder:
                        self.trajectory_recorder.record_agent_step(
                            step_number=step.step_number,
                            state=step.state.value,
                            llm_messages=messages,
                            llm_response=step.llm_response,
                            tool_calls=step.tool_calls,
                            tool_results=step.tool_results,
                            reflection=step.reflection,
                            error=step.error
                        )
                    
                    execution.steps.append(step)
                    break
            
            if step_number > self.max_steps and not execution.success:
                execution.final_result = "Task execution exceeded maximum steps without completion."
            
        except Exception as e:
            execution.final_result = f"Agent execution failed: {str(e)}"
        
        execution.execution_time = time.time() - start_time
        
        # Stop live display if running
        if self._live_display:
            self._live_display.stop()
            self._live_display = None
        
        # Display final summary
        if self.show_progress:
            self.console.print("\n")
            self.display_execution_summary(execution)
        
        return execution

    def reflect_on_result(self, tool_results: list[ToolResult]) -> str | None:
        """Reflect on tool execution result. Override for custom reflection logic."""
        if len(tool_results) == 0:
            return None
        
        reflection = ""
        for tool_result in tool_results:
            if not tool_result.success:
                reflection += f"The tool execution failed with error: {tool_result.error}. Consider trying a different approach or fixing the parameters.\n"
        
        return reflection

    def llm_indicates_task_completed(self, llm_response: LLMResponse) -> bool:
        """Check if the LLM indicates that the task is completed. Override for custom logic."""
        completion_indicators = [
            "task completed",
            "task finished",
            "done",
            "completed successfully",
            "finished successfully"
        ]
        
        response_lower = llm_response.content.lower()
        return any(indicator in response_lower for indicator in completion_indicators)

    def is_task_completed(self, llm_response: LLMResponse) -> bool:
        """Check if the task is completed based on the response. Override for custom logic."""
        return True
        
    
    def task_incomplete_message(self) -> str:
        """Return a message indicating that the task is incomplete. Override for custom logic."""
        return "The task is incomplete. Please try again."