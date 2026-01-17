"""
Base Agent - Shared infrastructure for all Karma agents.

All agents inherit from this base class which provides:
- OpenAI client setup
- Agent session management
- Reasoning chain tracking
- Tool calling capabilities
"""

import json
from datetime import datetime
from typing import Optional, Any
from abc import ABC, abstractmethod

from openai import OpenAI
from app.config import get_settings
from app.services.tools import save_reasoning
from .agent_tools import AGENT_TOOLS, execute_tool


class AgentSession:
    """Tracks the reasoning chain for a single agent interaction."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.started_at = datetime.now()
        self.thoughts: list[dict] = []
        self.tool_calls: list[dict] = []
    
    def add_thought(self, thought_type: str, content: str):
        """Add a thought to the reasoning chain."""
        self.thoughts.append({
            "type": thought_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name
        })
        print(f"🧠 [{self.agent_name}] {thought_type}: {content}")
    
    def add_tool_call(self, tool_name: str, args: dict, result: Any):
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name
        })
        print(f"🔧 [{self.agent_name}] Tool: {tool_name}")
    
    def get_reasoning_chain(self) -> list[str]:
        """Get the reasoning chain as a list of strings."""
        return [f"[{t['type']}] {t['content']}" for t in self.thoughts]
    
    def get_full_trace(self) -> dict:
        """Get the complete session trace."""
        return {
            "agent": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "duration_ms": (datetime.now() - self.started_at).total_seconds() * 1000,
            "thoughts": self.thoughts,
            "tool_calls": self.tool_calls
        }


class BaseAgent(ABC):
    """
    Base class for all Karma agents.
    
    Each agent has:
    - A unique name
    - A specialized system prompt
    - Access to the OpenAI API (if enabled)
    - A session for tracking reasoning
    - Dummy mode fallback (when OPENAI_KARMA != true)
    """
    
    # Override in subclasses
    AGENT_NAME = "BaseAgent"
    SYSTEM_PROMPT = "You are a helpful AI assistant."
    
    def __init__(self):
        settings = get_settings()
        self.settings = settings
        # Only create client if AI is explicitly enabled
        if settings.is_ai_enabled:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.dummy_mode = False
        else:
            self.client = None
            self.dummy_mode = True
        self.model = settings.openai_model
        self.session: Optional[AgentSession] = None
    
    def _is_available(self) -> bool:
        """Check if AI is available (not in dummy mode)."""
        return not self.dummy_mode and self.client is not None
    
    def _is_dummy_mode(self) -> bool:
        """Check if running in dummy mode."""
        return self.dummy_mode
    
    def _check_available_or_raise(self):
        """Check if AI is available, raise error if not."""
        if self._is_dummy_mode():
            raise ValueError(f"{self.AGENT_NAME} in DUMMY MODE. Set OPENAI_KARMA=true and OPENAI_API_KEY to enable AI.")
        if not self._is_available():
            raise ValueError(f"{self.AGENT_NAME} not configured. Please set OPENAI_API_KEY in your .env file.")
    
    def _start_session(self) -> AgentSession:
        """Start a new agent session."""
        self.session = AgentSession(self.AGENT_NAME)
        return self.session
    
    def _simple_completion(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """Execute a simple completion without tools."""
        self._check_available_or_raise()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _completion_with_tools(
        self,
        prompt: str,
        tools: list[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        max_iterations: int = 5
    ) -> dict:
        """
        Execute a completion with tool calling capabilities.
        
        Args:
            prompt: The user prompt
            tools: List of tool names to enable (None = all tools)
            temperature: Sampling temperature
            max_tokens: Max tokens per response
            max_iterations: Max tool call iterations
            
        Returns:
            dict with 'response', 'tool_calls', and 'tool_results'
        """
        self._check_available_or_raise()
        
        # Build tool definitions
        available_tools = tools or list(AGENT_TOOLS.keys())
        openai_tools = []
        
        for tool_name in available_tools:
            if tool_name in AGENT_TOOLS:
                tool_def = AGENT_TOOLS[tool_name]
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_def["description"],
                        "parameters": tool_def["parameters"]
                    }
                })
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        tool_calls_made = []
        tool_results = []
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice="auto" if openai_tools else None,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                message = response.choices[0].message
                
                # Check if AI wants to call tools
                if message.tool_calls:
                    messages.append(message)
                    
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        if self.session:
                            self.session.add_thought("tool_call", f"Calling {tool_name} with {tool_args}")
                        
                        # Execute the tool
                        result = execute_tool(tool_name, tool_args)
                        
                        tool_calls_made.append({
                            "tool": tool_name,
                            "args": tool_args
                        })
                        tool_results.append({
                            "tool": tool_name,
                            "result": result
                        })
                        
                        if self.session:
                            self.session.add_tool_call(tool_name, tool_args, result)
                        
                        # Add tool result to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result) if isinstance(result, dict) else str(result)
                        })
                else:
                    # No more tool calls - return final response
                    return {
                        "response": message.content,
                        "tool_calls": tool_calls_made,
                        "tool_results": tool_results,
                        "iterations": iterations
                    }
            
            except Exception as e:
                if self.session:
                    self.session.add_thought("error", f"Tool calling failed: {e}")
                raise
        
        # Max iterations reached - return last response
        return {
            "response": messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1]),
            "tool_calls": tool_calls_made,
            "tool_results": tool_results,
            "iterations": iterations,
            "max_iterations_reached": True
        }
    
    def _save_reasoning(self, decision_type: str, input_context: str, conclusion: str, confidence: float = 0.8):
        """Save the agent's reasoning to persistent storage."""
        if self.session:
            save_reasoning(
                decision_type=f"{self.AGENT_NAME}_{decision_type}",
                input_context=input_context,
                reasoning_steps=self.session.get_reasoning_chain(),
                conclusion=conclusion,
                confidence=confidence
            )
    
    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main entry point for the agent. Override in subclasses."""
        pass

