"""
Task Suggester Agent

Specializes in matching tasks to user context:
- Considers time available
- Matches energy levels
- Accounts for emotional state
- Learns from past feedback
"""

import json
import sys
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Task, TaskSuggestion, UserContext, EnergyLevel
from tools import get_learning_insights
from .base_agent import BaseAgent


class TaskSuggesterAgent(BaseAgent):
    """Agent that suggests the best task for the user's current context."""
    
    AGENT_NAME = "TaskSuggester"
    
    SYSTEM_PROMPT = """You are the Task Suggester Agent for Karma, a productivity app.

Your job is to select the BEST task for a user's current situation. Consider:

1. **Time Fit**: Task should be completable within available time
2. **Energy Match**: Don't suggest high-energy tasks to tired users
3. **Emotional Fit**: Match task mood to user's emotional state
4. **Past Patterns**: Learn from what worked before

You have access to the user's feedback history. Use it to make better suggestions.

Be thoughtful and explain your reasoning clearly."""

    async def run(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str] = None
    ) -> Optional[TaskSuggestion]:
        """
        Suggest the best task for the user's context.
        
        Args:
            tasks: Available tasks to choose from
            context: User's current context (time, energy, mood)
            excluded_task_ids: Task IDs to exclude (already suggested/rejected)
            
        Returns:
            TaskSuggestion with the recommended task and reasoning
        """
        self._start_session()
        excluded_task_ids = excluded_task_ids or []
        
        # Filter available tasks
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        if not available_tasks:
            self.session.add_thought("observation", "No tasks available after filtering")
            return None
        
        self.session.add_thought("observation", 
            f"Selecting from {len(available_tasks)} tasks for {context.time_available.value}min, {context.energy_level.value} energy")
        
        # Get learning insights
        insights = get_learning_insights()
        
        # Build task list for AI
        task_list = "\n".join([
            f"- ID: {t.id}\n  Task: \"{t.text}\"\n  Est: {t.estimated_minutes}min, Energy: {t.energy_required.value if t.energy_required else 'unknown'}, Category: {t.category.value if t.category else 'unknown'}"
            for t in available_tasks
        ])
        
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
        
        prompt = f"""Select the BEST task for this user right now.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}{emotional_context}
{learning_context}

AVAILABLE TASKS:
{task_list}

SELECTION CRITERIA:
1. Task must fit within {context.time_available.value} minutes
2. Energy requirement should match user's level ({context.energy_level.value})
3. Consider emotional fit if mood is provided
4. Prefer tasks that haven't been suggested recently

Return JSON:
{{
    "task_id": "<selected task ID>",
    "reasoning": "<2-3 sentences explaining why this is the best choice>",
    "confidence": <0.0-1.0>,
    "alternatives_note": "<brief note about other good options if any>"
}}

JSON response:"""

        try:
            response = self._simple_completion(prompt, temperature=0.5, max_tokens=400)
            
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
                    self.session.add_thought("conclusion", f"Selected: {selected_task.text}")
                    
                    self._save_reasoning(
                        decision_type="suggestion",
                        input_context=f"Context: {context.time_available.value}min, {context.energy_level.value}",
                        conclusion=f"Suggested: {selected_task.text}",
                        confidence=result.get("confidence", 0.7)
                    )
                    
                    return TaskSuggestion(
                        task=selected_task,
                        reasoning=result.get("reasoning", "This task matches your current context."),
                        confidence_score=min(1.0, max(0.0, result.get("confidence", 0.7)))
                    )
                else:
                    raise ValueError(f"AI selected unknown task ID: {result.get('task_id')}")
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task suggestion failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Suggestion failed: {e}")
            raise ValueError(f"Task suggestion failed: {e}")


# Singleton instance
task_suggester = TaskSuggesterAgent()

