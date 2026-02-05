"""
Task Suggester Agent

Specializes in matching tasks to user context:
- Considers time available
- Matches energy levels
- Accounts for emotional state
- Learns from past feedback
"""

import json
from typing import Optional

from app.models import Task, TaskSuggestion, UserContext, EnergyLevel, Subtask, SubtaskStatus
from app.services.tools import get_learning_insights
from .base_agent import BaseAgent


class TaskSuggesterAgent(BaseAgent):
    """Agent that suggests the best task for the user's current context."""
    
    AGENT_NAME = "TaskSuggester"
    
    SYSTEM_PROMPT = """You are the Task Suggester Agent for Karma, a productivity app.

Your job is to ALWAYS provide an actionable, low-friction suggestion - NEVER reject or say "no tasks match".

CRITICAL RULES:
1. **Always Suggest Something**: You must ALWAYS return a suggestion, even if no task perfectly matches
2. **Re-scope When Needed**: If a task doesn't fit time/mood, suggest a smaller subtask or lighter alternative
3. **Never Reject**: The goal is to ensure the user always gets an actionable suggestion, not a rejection

When evaluating tasks:
1. **Time Fit**: Task should be completable within available time
2. **Energy Match**: Don't suggest high-energy tasks to tired users
3. **Emotional Fit**: Match task mood to user's emotional state
4. **Past Patterns**: Learn from what worked before

If no task perfectly matches:
- Suggest a smaller subtask that fits the time (e.g., "work on section 1" instead of "finish report")
- Propose a similar but lighter task aligned with the same goal
- Break down a large task into a tiny first step

You have access to the user's feedback history. Use it to make better suggestions.

Be thoughtful and explain your reasoning clearly."""

    async def run(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str] = None,
        user_id: str = None
    ) -> Optional[TaskSuggestion]:
        """
        Suggest the best task for the user's context.
        
        Args:
            tasks: Available tasks to choose from
            context: User's current context (time, energy, mood)
            excluded_task_ids: Task IDs to exclude (already suggested/rejected)
            user_id: User ID for token usage tracking
            
        Returns:
            TaskSuggestion with the recommended task and reasoning
        """
        self._start_session()
        excluded_task_ids = excluded_task_ids or []
        
        # Filter available tasks
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        # CRITICAL: Never return None - always provide a suggestion
        # If no tasks available, we'll still suggest something via QuickWin in the route handler
        if not available_tasks:
            self.session.add_thought("observation", "No tasks available after filtering - this should be handled by route")
            # Return None here, but route will handle it with QuickWin
            return None
        
        self.session.add_thought("observation", 
            f"Selecting from {len(available_tasks)} tasks for {context.time_available.value}min, {context.energy_level.value} energy")
        
        # Check if in dummy mode
        if self._is_dummy_mode():
            return self._dummy_suggest(available_tasks, context)
        
        # Get learning insights
        insights = get_learning_insights()
        
        # Build task list for AI with subtask information
        task_list_parts = []
        for t in available_tasks:
            task_info = f"- ID: {t.id}\n  Task: \"{t.text}\"\n  Est: {t.estimated_minutes}min, Energy: {t.energy_required.value if t.energy_required else 'unknown'}, Category: {t.category.value if t.category else 'unknown'}"
            
            # Add subtask information if available
            if t.subtasks:
                pending_subtasks = [s for s in t.subtasks if s.status.value in ["pending", "in_progress"]]
                completed_count = len([s for s in t.subtasks if s.status.value == "completed"])
                
                if pending_subtasks:
                    task_info += f"\n  Has {len(pending_subtasks)} pending subtasks ({completed_count}/{len(t.subtasks)} completed)"
                    # List pending subtasks with their time estimates
                    for st in pending_subtasks[:3]:  # Show first 3 pending subtasks
                        task_info += f"\n    - Subtask: \"{st.instruction}\" ({st.estimated_minutes}min, status: {st.status.value})"
                    if len(pending_subtasks) > 3:
                        task_info += f"\n    ... and {len(pending_subtasks) - 3} more pending subtasks"
                else:
                    task_info += f"\n  Has {len(t.subtasks)} subtasks (all completed)"
            elif t.subtasks_generated:
                task_info += "\n  Subtasks were generated but none are pending"
            
            task_list_parts.append(task_info)
        
        task_list = "\n".join(task_list_parts)
        
        emotional_context = f", Mood: {context.emotional_state.value}" if context.emotional_state else ""
        
        # Include learning insights
        learning_context = ""
        if insights.get("total_feedback", 0) > 0:
            learning_context = f"""
LEARNING FROM PAST:
- Total feedback received: {insights.get('total_feedback', 0)}
- Acceptance rate: {insights.get('acceptance_rate', 0):.0%}
- Recent patterns: {insights.get('recent_patterns', 'No clear patterns yet')}
"""
        
        prompt = f"""Select the BEST task for this user right now. YOU MUST ALWAYS RETURN A SUGGESTION - NEVER REJECT.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}{emotional_context}
{learning_context}

AVAILABLE TASKS:
{task_list}

SELECTION STRATEGY (in priority order):
1. **Perfect Match**: Find a task/subtask that perfectly fits time, energy, and mood → suggest it directly
2. **Re-scope Task**: If no perfect match:
   a. For tasks with subtasks: Suggest a NEW smaller subtask that fits the time (e.g., if "Finish report" is too big, suggest "Write the introduction paragraph" or "Outline section 1")
   b. For tasks without subtasks: Suggest breaking it into a tiny first step (e.g., if "Organize garage" is too big, suggest "Take out 5 items from garage" or "Sort one box")
   c. Propose a similar but lighter alternative aligned with the same goal (e.g., if "Go to gym" doesn't fit, suggest "Do 10 push-ups at home")
3. **Best Available**: If nothing else works, suggest the closest match and explain how to adapt it

CRITICAL RULES:
- ALWAYS return a suggestion - never say "no tasks match"
- If a task is too large, suggest a smaller subtask or first step
- If energy doesn't match, suggest a lighter version of the same goal
- Make every suggestion actionable and low-friction
- Prefer suggesting existing subtasks that fit over creating new ones

IMPORTANT: For tasks with subtasks:
- If an existing subtask fits the time → suggest that subtask
- If no subtask fits but the task has subtasks → suggest creating a NEW smaller subtask (e.g., if task is "Call mom" and you have 5min, suggest "Find mom's phone number" or "Send mom a quick text")
- Always provide a specific, actionable subtask instruction

Return JSON:
{{
    "task_id": "<selected task ID - REQUIRED, must pick one>",
    "reasoning": "<2-3 sentences explaining why this is the best choice and how it fits their context>",
    "confidence": <0.0-1.0>,
    "suggest_subtask": <true/false - true if suggesting a subtask (existing or new)>,
    "subtask_instruction": "<specific instruction for the subtask if suggest_subtask is true, or null>",
    "subtask_estimated_minutes": <minutes for the subtask if suggest_subtask is true, or null>,
    "alternatives_note": "<brief note about other good options if any>",
    "is_rescoped": <true/false - true if you re-scoped the task into a smaller subtask>
}}

JSON response:"""

        try:
            response = await self._simple_completion(
                prompt, 
                temperature=0.5, 
                max_tokens=400,
                user_id=user_id,
                operation_type="suggest"
            )
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                
                # Find the selected task
                selected_task = next(
                    (t for t in available_tasks if t.id == result.get("task_id")),
                    None
                )
                
                if selected_task:
                    suggest_subtask = result.get("suggest_subtask", False)
                    subtask_instruction = result.get("subtask_instruction")
                    subtask_minutes = result.get("subtask_estimated_minutes")
                    
                    # If suggesting a subtask, find the matching existing subtask or create info for new one
                    suggested_subtask = None
                    if suggest_subtask and subtask_instruction:
                        # Check if this matches an existing pending subtask
                        pending_subtasks = [s for s in selected_task.subtasks if s.status.value in ["pending", "in_progress"]]
                        matching_subtask = next(
                            (s for s in pending_subtasks if subtask_instruction.lower() in s.instruction.lower() or s.instruction.lower() in subtask_instruction.lower()),
                            None
                        )
                        
                        if matching_subtask:
                            suggested_subtask = matching_subtask
                        else:
                            # Create a new subtask suggestion (will be created when user accepts)
                            suggested_subtask = Subtask(
                                step_number=len(selected_task.subtasks) + 1,
                                instruction=subtask_instruction,
                                estimated_minutes=subtask_minutes or min(context.time_available.value, 10),
                                status=SubtaskStatus.PENDING
                            )
                    
                    conclusion_text = f"Suggested: {selected_task.text}"
                    if suggest_subtask and subtask_instruction:
                        conclusion_text += f" - Subtask: {subtask_instruction}"
                    
                    self.session.add_thought("conclusion", conclusion_text)
                    
                    self._save_reasoning(
                        decision_type="suggestion",
                        input_context=f"Context: {context.time_available.value}min, {context.energy_level.value}",
                        conclusion=conclusion_text,
                        confidence=result.get("confidence", 0.7)
                    )
                    
                    # Create suggestion with subtask info if applicable
                    suggestion = TaskSuggestion(
                        task=selected_task,
                        reasoning=result.get("reasoning", "This task matches your current context."),
                        confidence_score=min(1.0, max(0.0, result.get("confidence", 0.7))),
                        suggested_subtask=suggested_subtask,
                        subtask_instruction=subtask_instruction if suggest_subtask else None,
                        subtask_estimated_minutes=subtask_minutes if suggest_subtask else None
                    )
                    
                    return suggestion
                else:
                    raise ValueError(f"AI selected unknown task ID: {result.get('task_id')}")
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task suggestion failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Suggestion failed: {e}")
            raise ValueError(f"Task suggestion failed: {e}")
    
    def _dummy_suggest(self, tasks: list[Task], context: UserContext) -> Optional[TaskSuggestion]:
        """Generate dummy suggestion when AI is not enabled."""
        self.session.add_thought("dummy_mode", "AI disabled - using dummy suggestion")
        
        # Simple matching: find first task that fits time and energy
        time_available = context.time_available.value
        energy = context.energy_level
        
        # Score tasks
        scored_tasks = []
        for task in tasks:
            score = 0
            
            # Time fit
            task_time = task.estimated_minutes or 15
            if task_time <= time_available:
                score += 2
            elif task_time <= time_available * 1.5:
                score += 1
            
            # Energy fit
            if task.energy_required:
                if task.energy_required == energy:
                    score += 2
                elif (energy == EnergyLevel.HIGH) or (energy == EnergyLevel.MEDIUM and task.energy_required == EnergyLevel.LOW):
                    score += 1
            
            scored_tasks.append((task, score))
        
        # Sort by score and pick best
        scored_tasks.sort(key=lambda x: x[1], reverse=True)
        
        if scored_tasks:
            selected_task = scored_tasks[0][0]
            selected_task.is_dummy = True
            
            self.session.add_thought("conclusion", f"[DUMMY] Selected: {selected_task.text}")
            
            return TaskSuggestion(
                task=selected_task,
                reasoning=f"[DUMMY MODE] Selected based on time ({selected_task.estimated_minutes or 15}min) and energy match. AI is disabled - set OPENAI_KARMA=true for smarter suggestions.",
                confidence_score=0.5
            )
        
        return None


# Singleton instance
task_suggester = TaskSuggesterAgent()

