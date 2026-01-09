"""AI service for task analysis, matching, and breakdown."""

import json
import random
from typing import Optional
from openai import OpenAI

from config import get_settings
from models import (
    Task, TaskStep, TaskBreakdown, TaskSuggestion, UserContext,
    EnergyLevel, EmotionalState, TimeAvailable, QuickWinTask,
    GENERIC_QUICKWIN_TASKS
)


class AIService:
    """Service for AI-powered task operations."""
    
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model
    
    def _is_available(self) -> bool:
        """Check if AI service is available."""
        return self.client is not None
    
    def _check_available_or_raise(self):
        """Check if AI is available, raise error if not."""
        if not self._is_available():
            raise ValueError("AI Agent not configured. Please set OPENAI_API_KEY in your .env file.")
    
    async def analyze_task(self, task: Task) -> Task:
        """
        Analyze a task to infer its properties.
        Uses AI to estimate duration, energy requirements, and emotional fit.
        """
        self._check_available_or_raise()
        
        prompt = f"""Analyze this task and estimate its properties. Return JSON only.

Task: "{task.text}"

Return a JSON object with:
- estimated_minutes: integer (5, 10, 15, 30, or 60)
- energy_required: "low", "medium", or "high"
- emotional_fit: array of emotions this task suits, from: ["stressed", "anxious", "calm", "happy", "tired", "motivated", "neutral"]

Example response:
{{"estimated_minutes": 15, "energy_required": "medium", "emotional_fit": ["calm", "motivated"]}}

JSON response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            task.estimated_minutes = result.get("estimated_minutes", 15)
            task.energy_required = EnergyLevel(result.get("energy_required", "medium"))
            task.emotional_fit = [
                EmotionalState(e) for e in result.get("emotional_fit", ["neutral"])
                if e in [es.value for es in EmotionalState]
            ]
            
        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"AI analysis failed: {e}")
        
        return task
    
    async def suggest_task(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str]
    ) -> Optional[TaskSuggestion]:
        """
        Suggest the best matching task for the user's context.
        Uses AI to match tasks to user's time, energy, and emotional state.
        """
        # Filter out already suggested tasks
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        if not available_tasks:
            return None
        
        self._check_available_or_raise()
        
        # Prepare task list for AI
        task_list = "\n".join([
            f"- ID: {t.id}, Task: \"{t.text}\", Est. Minutes: {t.estimated_minutes}, Energy: {t.energy_required.value if t.energy_required else 'unknown'}"
            for t in available_tasks
        ])
        
        emotional_context = f", Emotional State: {context.emotional_state.value}" if context.emotional_state else ""
        
        prompt = f"""You are helping a user find the best task to do right now.

User Context:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value}{emotional_context}

Available Tasks:
{task_list}

Select the BEST matching task for this user's current context. Consider:
1. Task should fit within available time
2. Task should match energy level (don't suggest high-energy tasks to tired users)
3. If emotional state is provided, consider emotional fit

Return JSON only:
{{"task_id": "selected-task-id", "reasoning": "brief explanation why this task is best", "confidence": 0.0-1.0}}

JSON response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            selected_task = next(
                (t for t in available_tasks if t.id == result.get("task_id")),
                None
            )
            
            if selected_task:
                return TaskSuggestion(
                    task=selected_task,
                    reasoning=result.get("reasoning", "This task matches your current context."),
                    confidence_score=min(1.0, max(0.0, result.get("confidence", 0.7)))
                )
            else:
                raise ValueError(f"AI selected unknown task ID: {result.get('task_id')}")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"AI suggestion failed: {e}")
    
    def get_generic_quickwin(self, context: UserContext) -> TaskSuggestion:
        """Get a generic quick win task when no suitable tasks available."""
        # Filter quick wins by energy level
        suitable_quickwins = GENERIC_QUICKWIN_TASKS.copy()
        
        if context.energy_level == EnergyLevel.LOW:
            # Prefer non-exercise tasks for low energy
            suitable_quickwins = [
                q for q in suitable_quickwins 
                if q.category != "exercise"
            ] or GENERIC_QUICKWIN_TASKS
        
        selected = random.choice(suitable_quickwins)
        
        # Convert to Task
        quickwin_task = Task(
            text=selected.text,
            estimated_minutes=selected.estimated_minutes,
            energy_required=EnergyLevel.LOW
        )
        
        return TaskSuggestion(
            task=quickwin_task,
            reasoning=f"Here's a quick {selected.category} activity to make the most of your time!",
            confidence_score=1.0,
            is_generic_quickwin=True
        )
    
    async def break_task_into_steps(self, task: Task, time_available: int) -> TaskBreakdown:
        """
        Break a task into actionable steps using AI.
        """
        self._check_available_or_raise()
        
        prompt = f"""Break this task into clear, actionable steps that can be completed in {time_available} minutes.

Task: "{task.text}"

Create 3-6 concrete steps. Each step should be:
- Specific and actionable
- Completable in a few minutes
- Clear enough to start immediately

Return JSON only:
{{
  "steps": [
    {{"step_number": 1, "instruction": "First step instruction", "estimated_minutes": 2}},
    {{"step_number": 2, "instruction": "Second step instruction", "estimated_minutes": 3}}
  ]
}}

JSON response:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            
            steps = [
                TaskStep(
                    step_number=s.get("step_number", i + 1),
                    instruction=s.get("instruction", "Complete this step"),
                    estimated_minutes=s.get("estimated_minutes")
                )
                for i, s in enumerate(result.get("steps", []))
            ]
            
            if steps:
                return TaskBreakdown(
                    task_id=task.id,
                    task_text=task.text,
                    steps=steps,
                    total_steps=len(steps)
                )
            else:
                raise ValueError("AI returned empty steps")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"AI task breakdown failed: {e}")


# Singleton instance
ai_service = AIService()
