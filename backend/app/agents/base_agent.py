"""
Base Agent - Shared infrastructure for all Karma agents.

All agents inherit from this base class which provides:
- OpenAI client setup
- Agent session management
- Reasoning chain tracking
- Tool calling capabilities
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Any
from abc import ABC, abstractmethod

from openai import OpenAI
from app.config import get_settings
from app.services.tools import save_reasoning
from app.services import db_service
from app.logging_config import get_logger
from .agent_tools import AGENT_TOOLS, execute_tool

logger = get_logger("BaseAgent")


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
    
    async def _check_token_limit(self, user_id: str, estimated_tokens: int) -> tuple[bool, dict]:
        """
        Check if user has enough tokens remaining for this operation.
        
        Returns:
            (allowed: bool, limit_info: dict)
        """
        if not user_id:
            return True, {}  # No limit check if no user_id
        
        try:
            allowed, limit_info = await db_service.check_token_limit(user_id, estimated_tokens)
            return allowed, limit_info
        except Exception as e:
            # If limit check fails, allow the request (fail open)
            print(f"⚠️ Failed to check token limit: {e}")
            return True, {}
    
    def _record_token_usage_async(self, user_id: str, prompt_tokens: int, completion_tokens: int, total_tokens: int, task_id: Optional[str] = None, operation_type: Optional[str] = None):
        """Helper to record token usage asynchronously (fire and forget)."""
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, schedule the coroutine
                loop.create_task(db_service.record_token_usage(
                    user_id=user_id,
                    agent_name=self.AGENT_NAME,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    model=self.model,
                    task_id=task_id,
                    operation_type=operation_type
                ))
            except RuntimeError:
                # No event loop running, create a new one (shouldn't happen in our async routes)
                asyncio.run(db_service.record_token_usage(
                    user_id=user_id,
                    agent_name=self.AGENT_NAME,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    model=self.model,
                    task_id=task_id,
                    operation_type=operation_type
                ))
        except Exception as e:
            # Don't fail the request if token tracking fails
            print(f"⚠️ Failed to record token usage: {e}")
    
    async def _simple_completion(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000, user_id: str = None, task_id: str = None, operation_type: str = None) -> str:
        """Execute a simple completion without tools."""
        self._check_available_or_raise()
        
        # Check token limit before making API call (estimate: prompt + max_tokens)
        if user_id:
            estimated_tokens = len(prompt.split()) * 1.3 + max_tokens  # Rough estimate
            allowed, limit_info = await self._check_token_limit(user_id, int(estimated_tokens))
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail=f"Monthly token limit exceeded. Used {limit_info.get('tokens_used_this_month', 0):,} / {limit_info.get('monthly_limit', 0):,} tokens this month."
                )
        
        logger.info(
            "%s LLM call: model=%s, temperature=%s, max_tokens=%s",
            self.AGENT_NAME, self.model, temperature, max_tokens,
        )
        logger.debug(
            "%s SYSTEM PROMPT sent to LLM:\n%s",
            self.AGENT_NAME, self.SYSTEM_PROMPT,
        )
        logger.debug(
            "%s USER PROMPT sent to LLM:\n%s",
            self.AGENT_NAME, prompt,
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        raw_response = response.choices[0].message.content
        logger.debug(
            "%s LLM raw response:\n%s",
            self.AGENT_NAME, raw_response,
        )
        
        if response.usage:
            logger.info(
                "%s LLM tokens used: %d total (%d prompt + %d completion)",
                self.AGENT_NAME,
                response.usage.total_tokens,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
        
        # Track token usage if user_id is provided (fire and forget)
        if user_id and response.usage:
            # Increment monthly usage counter
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(db_service.increment_token_usage(user_id, response.usage.total_tokens))
            except RuntimeError:
                asyncio.run(db_service.increment_token_usage(user_id, response.usage.total_tokens))
            
            # Record detailed usage
            self._record_token_usage_async(
                user_id=user_id,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                task_id=task_id,
                operation_type=operation_type
            )
        
        return raw_response
    
    async def _completion_with_tools(
        self,
        prompt: str,
        tools: list[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        max_iterations: int = 5,
        user_id: str = None,
        task_id: str = None,
        operation_type: str = None
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
        
        # Check token limit before first iteration (estimate: prompt + max_tokens * max_iterations)
        if user_id:
            estimated_tokens = len(prompt.split()) * 1.3 + (max_tokens * max_iterations)
            allowed, limit_info = await self._check_token_limit(user_id, int(estimated_tokens))
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail=f"Monthly token limit exceeded. Used {limit_info.get('tokens_used_this_month', 0):,} / {limit_info.get('monthly_limit', 0):,} tokens this month."
                )
        
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
                
                # Track token usage for each API call (accumulated across iterations)
                if user_id and response.usage:
                    # Increment monthly usage counter
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(db_service.increment_token_usage(user_id, response.usage.total_tokens))
                    except RuntimeError:
                        asyncio.run(db_service.increment_token_usage(user_id, response.usage.total_tokens))
                    
                    # Record detailed usage
                    self._record_token_usage_async(
                        user_id=user_id,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        total_tokens=response.usage.total_tokens,
                        task_id=task_id,
                        operation_type=operation_type
                    )
                
                message = response.choices[0].message
                
                # Check if AI wants to call tools
                if message.tool_calls:
                    # Append a plain dict so the next API call doesn't serialize OpenAI
                    # Pydantic models (which can cause by_alias=None errors)
                    msg_dict = {
                        "role": message.role,
                        "content": message.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": getattr(tc, "type", "function"),
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments or "{}",
                                },
                            }
                            for tc in message.tool_calls
                        ],
                    }
                    messages.append(msg_dict)
                    
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

