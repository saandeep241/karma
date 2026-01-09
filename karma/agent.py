"""
Agentic AI System for Karma
This is the core agent that autonomously reasons, plans, and executes.
"""

import json
from datetime import datetime
from typing import Optional, Any
from openai import OpenAI

from config import get_settings
from models import (
    Task, TaskStep, TaskBreakdown, TaskSuggestion, UserContext,
    EnergyLevel, EmotionalState, TaskCategory, GENERIC_QUICKWIN_TASKS
)
from tools import (
    AGENT_TOOLS, execute_tool, save_tasks, save_reasoning,
    record_user_feedback, get_learning_insights,
    save_task_with_details, get_rejected_task_ids
)


class AgentThought:
    """Represents a single thought in the agent's reasoning chain."""
    def __init__(self, thought_type: str, content: str, confidence: float = 0.0):
        self.timestamp = datetime.now()
        self.thought_type = thought_type  # observation, reasoning, plan, action, reflection
        self.content = content
        self.confidence = confidence
    
    def __str__(self):
        icons = {
            "observation": "👁️",
            "reasoning": "🧠",
            "plan": "📋",
            "action": "⚡",
            "reflection": "🔄",
            "tool_call": "🔧",
            "tool_result": "📤",
            "conclusion": "✅"
        }
        icon = icons.get(self.thought_type, "💭")
        return f"{icon} [{self.thought_type.upper()}] {self.content}"


class AgentSession:
    """Tracks the agent's session state and thought history."""
    def __init__(self):
        self.thoughts: list[AgentThought] = []
        self.tool_calls: list[dict] = []
        self.decisions: list[dict] = []
        self.start_time = datetime.now()
    
    def add_thought(self, thought_type: str, content: str, confidence: float = 0.0) -> AgentThought:
        thought = AgentThought(thought_type, content, confidence)
        self.thoughts.append(thought)
        print(thought)  # Print to console for visibility
        return thought
    
    def get_reasoning_chain(self) -> list[str]:
        return [t.content for t in self.thoughts if t.thought_type == "reasoning"]
    
    def get_full_trace(self) -> str:
        return "\n".join(str(t) for t in self.thoughts)


class KarmaAgent:
    """
    Agentic AI for Karma - Smart Task Suggestions
    
    This agent:
    1. Autonomously reasons about tasks and user context
    2. Calls tools to persist data and learn from feedback
    3. Maintains memory across sessions
    4. Reflects on past decisions to improve
    5. Plans multi-step actions
    """
    
    SYSTEM_PROMPT = """You are Karma, an intelligent AI agent that helps users make productive use of small time blocks.

You are AGENTIC - meaning you:
1. REASON step-by-step about every decision
2. CALL TOOLS to persist data, save reasoning, and learn from feedback
3. REMEMBER past interactions and learn from them
4. REFLECT on whether your suggestions were helpful
5. PLAN multi-step approaches when needed

For EVERY decision, you must:
1. First OBSERVE the input and context
2. Then REASON through your thought process step by step
3. Consider PAST LEARNINGS if available
4. Make a DECISION with confidence level
5. SAVE your reasoning using the save_reasoning tool
6. Take ACTION (suggest task, break down task, etc.)

Always be transparent about your reasoning. Users can see your thought process.

When suggesting tasks:
- Consider time available, energy level, and emotional state
- Learn from past accept/reject patterns
- Explain WHY you're suggesting each task
- Save all reasoning for transparency

Available tools: save_tasks, load_tasks, save_reasoning, record_user_feedback, get_learning_insights, analyze_task_properties, select_best_task, break_into_steps"""

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model
        self.session = AgentSession()
    
    def _is_available(self) -> bool:
        return self.client is not None
    
    def _check_available_or_raise(self):
        """Check if AI is available, raise error if not."""
        if not self._is_available():
            raise ValueError("AI Agent not configured. Please set OPENAI_API_KEY in your .env file.")
    
    def _call_llm(self, messages: list[dict], tools: list[dict] = None) -> dict:
        """Call the LLM with optional tool use."""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0]
    
    def _execute_agent_loop(self, user_message: str, max_iterations: int = 5) -> dict:
        """
        The core agent loop - reason, plan, act, observe, repeat.
        """
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        self.session.add_thought("observation", f"Received request: {user_message[:100]}...")
        
        iteration = 0
        final_response = None
        
        while iteration < max_iterations:
            iteration += 1
            self.session.add_thought("reasoning", f"Agent loop iteration {iteration}")
            
            # Call LLM with tools
            response = self._call_llm(messages, AGENT_TOOLS)
            
            # Check if we got tool calls
            if response.message.tool_calls:
                # Process each tool call
                for tool_call in response.message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    self.session.add_thought(
                        "tool_call",
                        f"Calling {tool_name} with args: {json.dumps(tool_args)[:100]}..."
                    )
                    
                    # Execute the tool
                    result = execute_tool(tool_name, tool_args)
                    
                    self.session.add_thought(
                        "tool_result",
                        f"Tool {tool_name} returned: {json.dumps(result)[:100]}..."
                    )
                    
                    self.session.tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })
                    
                    # Add tool result to messages
                    messages.append(response.message)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
            else:
                # No more tool calls - we have final response
                final_response = response.message.content
                self.session.add_thought("conclusion", f"Final response ready")
                break
        
        return {
            "response": final_response,
            "thoughts": self.session.get_full_trace(),
            "tool_calls": self.session.tool_calls,
            "iterations": iteration
        }
    
    async def analyze_tasks(self, tasks: list[Task]) -> tuple[list[Task], dict]:
        """
        Analyze tasks using agentic reasoning.
        Returns analyzed tasks and full reasoning trace.
        """
        self.session = AgentSession()  # Fresh session
        
        self._check_available_or_raise()
        
        self.session.add_thought("observation", f"Analyzing {len(tasks)} tasks")
        
        # Save tasks first
        today = datetime.now().strftime("%Y-%m-%d")
        task_texts = [t.text for t in tasks]
        save_result = save_tasks(task_texts, today)
        self.session.add_thought("action", f"Saved tasks to {save_result['filepath']}")
        
        # Analyze each task with reasoning
        analyzed_tasks = []
        all_reasoning = []
        
        for task in tasks:
            self.session.add_thought("reasoning", f"Analyzing task: {task.text}")
            
            prompt = f"""Analyze this task and determine its properties.

Task: "{task.text}"

Think step by step:
1. What CATEGORY is this task? Choose ONE from: work, personal, health, finance, learning, social, home, errands, creative, admin, other
2. What type of task is this? (communication, organization, creative, research, etc.)
3. How long would this typically take? (5, 10, 15, 30, or 60 minutes)
4. What energy level does this require? (low, medium, high)
5. What emotional states is this task suitable for?
6. What additional TAGS apply? (e.g., "urgent", "quick-win", "deep-work", "collaborative", "deadline", etc.)

Then call the save_reasoning tool with your analysis, and return JSON:
{{"category": "work|personal|health|finance|learning|social|home|errands|creative|admin|other", "tags": ["tag1", "tag2"], "estimated_minutes": int, "energy_required": "low|medium|high", "emotional_fit": ["emotion1", "emotion2"], "task_type": "type", "reasoning_summary": "brief explanation"}}"""

            try:
                result = self._execute_agent_loop(prompt, max_iterations=3)
                
                # Parse the response
                response_text = result["response"] or ""
                
                # Try to extract JSON from response
                try:
                    # Find JSON in response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        analysis = json.loads(response_text[json_start:json_end])
                        
                        task.estimated_minutes = analysis.get("estimated_minutes", 15)
                        task.energy_required = EnergyLevel(analysis.get("energy_required", "medium"))
                        task.emotional_fit = [
                            EmotionalState(e) for e in analysis.get("emotional_fit", ["neutral"])
                            if e in [es.value for es in EmotionalState]
                        ]
                        
                        # Auto-tagging
                        category_str = analysis.get("category", "other").lower()
                        if category_str in [c.value for c in TaskCategory]:
                            task.category = TaskCategory(category_str)
                        else:
                            task.category = TaskCategory.OTHER
                        
                        task.tags = analysis.get("tags", [])
                        task.task_type = analysis.get("task_type")
                        
                        all_reasoning.append({
                            "task": task.text,
                            "analysis": analysis,
                            "thoughts": result["thoughts"]
                        })
                except json.JSONDecodeError:
                    self.session.add_thought("reflection", f"Failed to parse AI response for task: {task.text}")
                
            except Exception as e:
                self.session.add_thought("reflection", f"Analysis failed for task: {e}")
            
            analyzed_tasks.append(task)
        
        # Save overall reasoning
        save_reasoning(
            decision_type="task_analysis",
            input_context=f"Analyzed {len(tasks)} tasks",
            reasoning_steps=self.session.get_reasoning_chain(),
            conclusion=f"Successfully analyzed {len(analyzed_tasks)} tasks",
            confidence=0.8
        )
        
        return analyzed_tasks, {
            "reasoning": self.session.get_full_trace(),
            "task_analyses": all_reasoning
        }
    
    async def suggest_task(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str]
    ) -> tuple[Optional[TaskSuggestion], dict]:
        """
        Suggest a task using agentic reasoning with learning.
        Returns suggestion and full reasoning trace.
        """
        self.session = AgentSession()
        
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        if not available_tasks:
            return None, {"reasoning": "No tasks available"}
        
        self._check_available_or_raise()
        
        self.session.add_thought("observation", f"Suggesting from {len(available_tasks)} tasks")
        self.session.add_thought("observation", f"User context: {context.time_available.value}min, {context.energy_level.value} energy")
        
        # First, get learning insights
        insights = get_learning_insights("all")
        self.session.add_thought("reasoning", f"Past insights: {insights.get('acceptance_rate', 0):.0%} acceptance rate")
        
        # Prepare task info
        task_info = "\n".join([
            f"- ID: {t.id}\n  Text: \"{t.text}\"\n  Est. Minutes: {t.estimated_minutes}\n  Energy: {t.energy_required.value if t.energy_required else 'unknown'}"
            for t in available_tasks
        ])
        
        emotional_context = f"\n- Emotional State: {context.emotional_state.value}" if context.emotional_state else ""
        
        insights_context = ""
        if insights.get("patterns"):
            insights_context = f"\n\nPast Learning Insights:\n- Overall acceptance rate: {insights.get('acceptance_rate', 0):.0%}\n"
            for pattern in insights.get("patterns", []):
                insights_context += f"- When {pattern['type']}={pattern['value']}: {pattern['acceptance_rate']:.0%} acceptance\n"
        
        prompt = f"""You are selecting the best task for a user. Think through this carefully.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}{emotional_context}
{insights_context}

AVAILABLE TASKS:
{task_info}

INSTRUCTIONS:
1. First, reason through each task's fit for this user's context
2. Consider past learning insights if available
3. Call save_reasoning with your step-by-step thought process
4. Select the BEST task and explain WHY

Return JSON:
{{"task_id": "selected-id", "reasoning": "detailed explanation of why this task is best for the user right now", "confidence": 0.0-1.0, "alternative_ids": ["other-good-options"]}}"""

        try:
            result = self._execute_agent_loop(prompt, max_iterations=5)
            response_text = result["response"] or ""
            
            # Parse response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                selection = json.loads(response_text[json_start:json_end])
                
                selected_task = next(
                    (t for t in available_tasks if t.id == selection.get("task_id")),
                    None
                )
                
                if selected_task:
                    suggestion = TaskSuggestion(
                        task=selected_task,
                        reasoning=selection.get("reasoning", "This task matches your context."),
                        confidence_score=min(1.0, max(0.0, selection.get("confidence", 0.7)))
                    )
                    
                    # Save the reasoning
                    save_reasoning(
                        decision_type="task_suggestion",
                        input_context=f"Context: {context.time_available.value}min, {context.energy_level.value} energy",
                        reasoning_steps=self.session.get_reasoning_chain(),
                        conclusion=f"Selected: {selected_task.text}",
                        confidence=suggestion.confidence_score
                    )
                    
                    return suggestion, {
                        "reasoning": self.session.get_full_trace(),
                        "selection": selection,
                        "tool_calls": result["tool_calls"]
                    }
        
        except Exception as e:
            self.session.add_thought("reflection", f"Suggestion failed: {e}")
            raise ValueError(f"AI suggestion failed: {e}")
    
    async def break_task_into_steps(
        self,
        task: Task,
        time_available: int
    ) -> tuple[TaskBreakdown, dict]:
        """
        Break a task into steps using agentic reasoning.
        """
        self.session = AgentSession()
        
        self._check_available_or_raise()
        
        self.session.add_thought("observation", f"Breaking down: {task.text}")
        self.session.add_thought("observation", f"Time available: {time_available} minutes")
        
        prompt = f"""Break this task into clear, actionable steps.

TASK: "{task.text}"
TIME AVAILABLE: {time_available} minutes

INSTRUCTIONS:
1. Think about what this task actually involves
2. Break it into 3-6 concrete, actionable steps
3. Each step should be specific enough to start immediately
4. Estimate time for each step (should sum to ~{time_available} minutes)
5. Call save_reasoning with your breakdown logic

Return JSON:
{{
  "steps": [
    {{"step_number": 1, "instruction": "Clear action to take", "estimated_minutes": 2, "why": "reason this step is needed"}},
    ...
  ],
  "breakdown_reasoning": "explanation of how you broke this down"
}}"""

        try:
            result = self._execute_agent_loop(prompt, max_iterations=3)
            response_text = result["response"] or ""
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                breakdown_data = json.loads(response_text[json_start:json_end])
                
                steps = [
                    TaskStep(
                        step_number=s.get("step_number", i + 1),
                        instruction=s.get("instruction", "Complete this step"),
                        estimated_minutes=s.get("estimated_minutes")
                    )
                    for i, s in enumerate(breakdown_data.get("steps", []))
                ]
                
                if steps:
                    breakdown = TaskBreakdown(
                        task_id=task.id,
                        task_text=task.text,
                        steps=steps,
                        total_steps=len(steps)
                    )
                    
                    save_reasoning(
                        decision_type="task_breakdown",
                        input_context=f"Task: {task.text}, Time: {time_available}min",
                        reasoning_steps=self.session.get_reasoning_chain(),
                        conclusion=f"Created {len(steps)} steps",
                        confidence=0.85
                    )
                    
                    return breakdown, {
                        "reasoning": self.session.get_full_trace(),
                        "breakdown_data": breakdown_data
                    }
        
        except Exception as e:
            self.session.add_thought("reflection", f"Breakdown failed: {e}")
            raise ValueError(f"AI task breakdown failed: {e}")
    
    def record_feedback(self, task: Task, context: UserContext, accepted: bool, reasoning: str):
        """Record user feedback for learning."""
        self.session = AgentSession()
        self.session.add_thought("observation", f"User {'accepted' if accepted else 'rejected'}: {task.text}")
        
        result = record_user_feedback(
            task_text=task.text,
            accepted=accepted,
            task_id=task.id,
            user_context={
                "time_available": context.time_available.value,
                "energy_level": context.energy_level.value,
                "emotional_state": context.emotional_state.value if context.emotional_state else None
            },
            reasoning_used=reasoning
        )
        
        feedback_msg = "accepted and will be used for task breakdown" if accepted else "rejected and won't be suggested again in similar context"
        self.session.add_thought("reflection", f"Task {feedback_msg}. Overall acceptance rate: {result.get('acceptance_rate', 0):.0%}")
        
        # Save reflection
        save_reasoning(
            decision_type="reflection",
            input_context=f"User feedback on: {task.text}",
            reasoning_steps=[
                f"User {'accepted' if accepted else 'rejected'} the suggestion",
                f"Task ID: {task.id}",
                f"Context was: {context.time_available.value}min, {context.energy_level.value} energy",
                f"Reasoning provided was: {reasoning[:100]}..." if reasoning else "No reasoning provided",
                f"Current overall acceptance rate: {result.get('acceptance_rate', 0):.0%}",
                f"Action: {'Proceeding to task breakdown' if accepted else 'Task added to rejection list for this context'}"
            ],
            conclusion=f"Feedback recorded - task {'will be broken down' if accepted else 'excluded from future suggestions in similar context'}",
            confidence=1.0
        )
        
        return result
    
    async def generate_quickwin(self, context: UserContext) -> dict:
        """
        Generate a personalized quick win using AI based on user's context.
        This creates a unique, context-aware micro-task.
        """
        self.session = AgentSession()
        self.session.add_thought("observation", f"Generating quick win for: {context.time_available.value}min, {context.energy_level.value} energy, {context.emotional_state.value if context.emotional_state else 'neutral'} mood")
        
        self._check_available_or_raise()
        
        mood_context = context.emotional_state.value if context.emotional_state else "neutral"
        
        prompt = f"""You are a productivity coach. Generate ONE specific, actionable micro-task that someone can do RIGHT NOW.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}
- Current Mood: {mood_context}

REQUIREMENTS:
1. The task must be completable in {context.time_available.value} minutes or less
2. Match the energy level: {"simple, low-effort tasks" if context.energy_level.value == "low" else "moderate effort tasks" if context.energy_level.value == "medium" else "engaging, productive tasks"}
3. Consider the mood: {"calming, stress-reducing activities" if mood_context in ["stressed", "anxious"] else "energizing activities" if mood_context in ["tired", "sleepy"] else "productive activities" if mood_context in ["motivated", "focused"] else "balanced activities"}
4. Be SPECIFIC - not "organize something" but "organize the top drawer of your desk"
5. Make it immediately actionable - no preparation needed

Return JSON:
{{
    "task": "The specific task to do (be detailed and actionable)",
    "category": "one of: wellness, productivity, social, creative, organization, exercise, mindfulness, learning",
    "estimated_minutes": {min(context.time_available.value, 10)},
    "why_this_task": "Brief explanation of why this task is perfect for their current state",
    "first_step": "The very first action to take"
}}"""

        try:
            result = self._execute_agent_loop(prompt, max_iterations=2)
            response_text = result["response"] or ""
            
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                quickwin_data = json.loads(response_text[json_start:json_end])
                
                self.session.add_thought("conclusion", f"Generated: {quickwin_data.get('task', 'Unknown task')}")
                
                save_reasoning(
                    decision_type="quickwin_generation",
                    input_context=f"Context: {context.time_available.value}min, {context.energy_level.value}, {mood_context}",
                    reasoning_steps=self.session.get_reasoning_chain(),
                    conclusion=f"Generated quick win: {quickwin_data.get('task', '')}",
                    confidence=0.9
                )
                
                return {
                    "text": quickwin_data.get("task", "Take a short break"),
                    "category": quickwin_data.get("category", "wellness"),
                    "estimated_minutes": quickwin_data.get("estimated_minutes", 5),
                    "reasoning": quickwin_data.get("why_this_task", "This matches your current energy and time."),
                    "first_step": quickwin_data.get("first_step", "Start now!"),
                    "ai_generated": True
                }
        
        except Exception as e:
            self.session.add_thought("reflection", f"Quick win generation failed: {e}")
            raise ValueError(f"AI quick win generation failed: {e}")
    
    async def enrich_task(self, task: Task) -> dict:
        """
        Add Task Agent - Enriches a task with research, questions, and resources.
        This agent is triggered when a new task is added.
        """
        self.session = AgentSession()
        self.session.add_thought("observation", f"Add Task Agent activated for: {task.text} (ID: {task.id})")
        
        self._check_available_or_raise()
        
        prompt = f"""You are the Add Task Agent. Your job is to enrich a newly added task with helpful information.

TASK: "{task.text}"
TASK ID: "{task.id}"

Analyze this task and provide SPECIFIC, ACTIONABLE information:

1. **Estimated Time**: How long will this task realistically take? (in minutes)
2. **Steps to Complete**: What are the specific steps needed? (3-6 steps)
3. **Probable Questions**: What should the user figure out before starting? (3-5 questions)
4. **Suggested Resources**: What websites, tools, or resources would help? (2-4 specific resources)
5. **Potential Blockers**: What might prevent completion? (2-3 blockers)
6. **Success Criteria**: How will they know it's done? (2-4 criteria)

Be SPECIFIC to this task. For example, if it's about passports, mention specific government websites, documents needed, etc.

Return JSON:
{{
    "estimated_minutes": 60,
    "steps": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
    "probable_questions": ["What documents do I need?", ...],
    "suggested_resources": ["Official government website: ...", "Required forms: ...", ...],
    "potential_blockers": ["Missing documents", ...],
    "success_criteria": ["Application submitted", "Confirmation received", ...],
    "agent_notes": "Additional helpful tips specific to this task"
}}"""

        try:
            result = self._execute_agent_loop(prompt, max_iterations=3)
            response_text = result["response"] or ""
            
            # Parse response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                enrichment_data = json.loads(response_text[json_start:json_end])
                
                # Save enrichment with correct task ID
                from tools import TASK_DETAILS_DIR
                enrichment_filepath = TASK_DETAILS_DIR / f"{task.id}_enrichment.json"
                
                enrichment = {
                    "task_id": task.id,
                    "task_text": task.text,
                    "enriched_at": datetime.now().isoformat(),
                    "estimated_minutes": enrichment_data.get("estimated_minutes", 30),
                    "steps": enrichment_data.get("steps", []),
                    "probable_questions": enrichment_data.get("probable_questions", []),
                    "suggested_resources": enrichment_data.get("suggested_resources", []),
                    "related_topics": enrichment_data.get("related_topics", []),
                    "potential_blockers": enrichment_data.get("potential_blockers", []),
                    "success_criteria": enrichment_data.get("success_criteria", []),
                    "agent_notes": enrichment_data.get("agent_notes", ""),
                    "agent_reasoning": self.session.get_full_trace()
                }
                
                with open(enrichment_filepath, 'w') as f:
                    json.dump(enrichment, f, indent=2)
                
                print(f"📝 [ENRICHMENT] Saved to {enrichment_filepath}")
                
                self.session.add_thought("conclusion", f"Task enriched with {len(enrichment.get('steps', []))} steps, {len(enrichment['probable_questions'])} questions")
                
                # Save reasoning
                save_reasoning(
                    decision_type="task_enrichment",
                    input_context=f"Enriching task: {task.text}",
                    reasoning_steps=self.session.get_reasoning_chain(),
                    conclusion=f"Added {len(enrichment.get('steps', []))} steps, {len(enrichment['probable_questions'])} questions, {len(enrichment['success_criteria'])} success criteria",
                    confidence=0.85
                )
                
                return enrichment
        
        except Exception as e:
            self.session.add_thought("reflection", f"AI enrichment failed: {e}")
            raise ValueError(f"AI task enrichment failed: {e}")
    


# Singleton instance
karma_agent = KarmaAgent()

