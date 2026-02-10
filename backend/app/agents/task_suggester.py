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
from app.logging_config import get_logger
from .base_agent import BaseAgent

logger = get_logger("TaskSuggester")


class TaskSuggesterAgent(BaseAgent):
    """Agent that suggests the best task for the user's current context."""
    
    AGENT_NAME = "TaskSuggester"
    
    SYSTEM_PROMPT = """You are the Task Suggester Agent for Karma, a productivity app.

Your job is to suggest a task or subtask from the user's provided task list that best fits their available time and energy. 

CRITICAL RULES:
1. **Prioritize User Tasks**: Your primary goal is to find the best match among the tasks the user has already created.
2. **Prefer a fit**: Suggest a task or subtask that fits within available time and energy when one exists.
3. **Do not re-scope when nothing fits**: If no task or subtask fits within the user's time and energy, do not suggest re-scoping (e.g. "do just the first part"). Instead set suggest_quickwin to true so the system will suggest a QuickWin activity that fits.
4. **Time and energy matter**: Only suggest a task/subtask if its estimated time is within available time and energy level is compatible.

When evaluating tasks:
1. **Time Fit**: Task or subtask must be completable within available time.
2. **Energy Match**: Don't suggest high-energy tasks to tired users.
3. **Emotional Fit**: Match task mood to user's emotional state when possible.
4. **Past Patterns**: Learn from what worked before.

If no task or subtask fits within time and energy: set suggest_quickwin to true. The system will then suggest a short QuickWin activity that fits.

Be thoughtful and explain your reasoning clearly, specifically highlighting why the chosen user task is a good match for their current context."""

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
        
        # Filter available tasks (excluded = previously suggested / skipped / completed in this flow)
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        # CRITICAL: Never return None - always provide a suggestion
        # If no tasks available, we'll still suggest something via QuickWin in the route handler
        if not available_tasks:
            self.session.add_thought(
                "observation",
                f"No tasks available after filtering (excluded {len(excluded_task_ids)} IDs: previously suggested/skipped/completed)"
            )
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
        
        prompt = f"""Select the BEST task from the user's list for them right now.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}{emotional_context}
{learning_context}

AVAILABLE USER TASKS:
{task_list}

SELECTION STRATEGY (in priority order):
1. **Perfect Match**: Find a task or subtask from the list above that fits within the user's available time AND energy → suggest it directly (set task_id, suggest_quickwin: false).
2. **Nothing fits**: If NO task or subtask from the user's list fits within the available time and energy, set suggest_quickwin to true. The system will then suggest a QuickWin activity that fits.

CRITICAL RULES:
- Only suggest a task or subtask if its estimated time is within available time and energy is compatible.
- Your primary focus is finding the best match from the AVAILABLE USER TASKS provided above.
- If no task or subtask fits within available time and energy, set suggest_quickwin to true - do not pick a task or re-scope.
- When you suggest a task, make it actionable and low-friction.
- Prefer suggesting existing subtasks that fit over creating new ones.

For tasks with subtasks (only when suggesting a task that fits):
- If an existing subtask fits the time → suggest that subtask.
- If no subtask fits but the task has subtasks and the full task fits → you may suggest the task; otherwise use suggest_quickwin.

Return JSON:
{{
    "suggest_quickwin": <true if no user task/subtask fits time and energy, false if suggesting a task>,
    "task_id": "<selected task ID when suggest_quickwin is false - required when suggesting a task; null when suggest_quickwin is true>",
    "reasoning": "<2-3 sentences explaining your choice, specifically why this user task is the best fit>",
    "confidence": <0.0-1.0>,
    "suggest_subtask": <true/false - true if suggesting a subtask (existing or new), only when suggest_quickwin is false>,
    "subtask_instruction": "<specific instruction for the subtask if suggest_subtask is true, or null>",
    "subtask_estimated_minutes": <minutes for the subtask if suggest_subtask is true, or null>,
    "alternatives_note": "<brief note about other good options from the user's list if any>",
    "is_rescoped": <true/false - true if you re-scoped the task into a smaller subtask>
}}

JSON response:"""

        # Log LLM request context for debugging (why a task was or wasn't picked)
        logger.info(
            "TaskSuggester LLM request: time_available=%s min, energy=%s. Tasks sent to LLM:\n%s",
            context.time_available.value,
            context.energy_level.value,
            task_list,
        )
        logger.debug("TaskSuggester full LLM prompt:\n%s", prompt)

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
                
                # If AI determined nothing fits time/energy, signal QuickWin (return None)
                if result.get("suggest_quickwin") is True:
                    logger.info(
                        "TaskSuggester LLM response (suggest_quickwin=true): %s",
                        json.dumps(result, indent=2),
                    )
                    self.session.add_thought(
                        "conclusion",
                        "No task fits time/energy; suggesting QuickWin instead"
                    )
                    return None
                
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
        
        # If no task fits time and energy (best score 0), return None so route uses QuickWin
        if scored_tasks and scored_tasks[0][1] == 0:
            self.session.add_thought(
                "conclusion",
                "[DUMMY] No task fits time/energy; route will suggest QuickWin"
            )
            return None
        
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

