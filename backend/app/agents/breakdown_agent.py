"""
Breakdown Agent

Specializes in breaking tasks into actionable subtasks:
- Creates clear, specific subtasks with time estimates
- Each subtask has its own status (pending/in_progress/completed)
- Estimates time for each subtask based on reasoning
- Makes tasks less overwhelming
"""

import json

from app.models import Task, TaskStep, TaskBreakdown, Subtask, SubtaskStatus
from .base_agent import BaseAgent


class BreakdownAgent(BaseAgent):
    """Agent that breaks tasks into actionable subtasks with time estimates."""
    
    AGENT_NAME = "Breakdown"
    
    SYSTEM_PROMPT = """You are the Breakdown Agent for Karma, a productivity app.

Your job is to break tasks into clear, actionable SUBTASKS that eliminate decision paralysis.

Guidelines:
1. Each subtask should be SPECIFIC and immediately actionable
2. Subtasks should be small enough to feel achievable
3. First subtask should be the easiest to reduce friction
4. Include REALISTIC time estimates with reasoning for each
5. Order subtasks logically

Bad subtask: "Work on the report"
Good subtask: "Open the report document and read the last paragraph you wrote" (2 min - just opening and reading)

Bad subtask: "Research the topic"  
Good subtask: "Google '[specific query]' and open the top 3 results" (3 min - quick search)

Make each subtask so clear that there's no ambiguity about what to do.
Time estimates should be REALISTIC based on the actual work involved."""

    async def run(self, task: Task, time_available: int) -> TaskBreakdown:
        """
        Break a task into actionable subtasks with time estimates.
        
        Args:
            task: The task to break down
            time_available: Minutes available to work on this
            
        Returns:
            TaskBreakdown with subtasks
        """
        self._start_session()
        self.session.add_thought("observation", f"Breaking down: {task.text} ({time_available}min)")
        
        # Check if in dummy mode
        if self._is_dummy_mode():
            return self._dummy_breakdown(task, time_available)
        
        prompt = f"""Break this task into clear, actionable subtasks with time estimates.

TASK: "{task.text}"
TIME AVAILABLE: {time_available} minutes

Create 3-6 specific subtasks that:
1. Are immediately actionable (no thinking required)
2. Are small enough to feel achievable
3. Have clear completion criteria
4. Have REALISTIC time estimates with reasoning
5. Sum to approximately {time_available} minutes

Return JSON:
{{
    "subtasks": [
        {{
            "step_number": 1,
            "instruction": "<specific action to take>",
            "estimated_minutes": <number>,
            "time_reasoning": "<why this takes X minutes>"
        }},
        {{
            "step_number": 2,
            "instruction": "<specific action to take>",
            "estimated_minutes": <number>,
            "time_reasoning": "<why this takes X minutes>"
        }}
    ],
    "total_time": <sum of all subtask times>,
    "breakdown_reasoning": "<brief explanation of your approach>"
}}

JSON response:"""

        try:
            response = self._simple_completion(prompt, temperature=0.5, max_tokens=1000)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                breakdown_data = json.loads(response[json_start:json_end])
                
                # Create TaskStep objects for backward compatibility
                steps = []
                subtasks = []
                total_time = 0
                
                for i, s in enumerate(breakdown_data.get("subtasks", breakdown_data.get("steps", []))):
                    step_num = s.get("step_number", i + 1)
                    instruction = s.get("instruction", "Complete this step")
                    est_minutes = s.get("estimated_minutes", 5)
                    time_reasoning = s.get("time_reasoning", "")
                    
                    # Create TaskStep for backward compatibility
                    steps.append(TaskStep(
                        step_number=step_num,
                        instruction=instruction,
                        estimated_minutes=est_minutes
                    ))
                    
                    # Create Subtask with status tracking
                    subtasks.append(Subtask(
                        step_number=step_num,
                        instruction=instruction,
                        estimated_minutes=est_minutes,
                        status=SubtaskStatus.PENDING,
                        ai_reasoning=time_reasoning
                    ))
                    
                    total_time += est_minutes
                
                if not steps:
                    raise ValueError("AI returned no subtasks")
                
                breakdown = TaskBreakdown(
                    task_id=task.id,
                    task_text=task.text,
                    steps=steps,
                    total_steps=len(steps),
                    total_estimated_minutes=total_time
                )
                
                # Also update the task with subtasks
                task.subtasks = subtasks
                task.subtasks_generated = True
                task.estimated_minutes = total_time
                
                self.session.add_thought("conclusion", f"Created {len(steps)} subtasks, total {total_time}min")
                
                self._save_reasoning(
                    decision_type="breakdown",
                    input_context=f"Task: {task.text}, Time: {time_available}min",
                    conclusion=f"Created {len(steps)} subtasks totaling {total_time}min",
                    confidence=0.85
                )
                
                return breakdown
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task breakdown failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Breakdown failed: {e}")
            raise ValueError(f"Task breakdown failed: {e}")
    
    def _dummy_breakdown(self, task: Task, time_available: int) -> TaskBreakdown:
        """Generate dummy breakdown when AI is not enabled."""
        self.session.add_thought("dummy_mode", "AI disabled - using dummy breakdown")
        
        # Simple heuristic breakdown
        num_steps = min(4, max(2, time_available // 10))
        time_per_step = time_available // num_steps
        
        steps = []
        subtasks = []
        
        dummy_actions = [
            "Get started by opening/preparing what you need",
            "Work on the main part of the task",
            "Review what you've done",
            "Finish up and save your progress"
        ]
        
        for i in range(num_steps):
            step = TaskStep(
                step_number=i + 1,
                instruction=dummy_actions[i] if i < len(dummy_actions) else 'Continue working',
                estimated_minutes=time_per_step
            )
            steps.append(step)
            
            subtask = Subtask(
                step_number=i + 1,
                instruction=dummy_actions[i] if i < len(dummy_actions) else 'Continue working',
                estimated_minutes=time_per_step,
                status=SubtaskStatus.PENDING,
                ai_reasoning=None
            )
            subtasks.append(subtask)
        
        breakdown = TaskBreakdown(
            task_id=task.id,
            task_text=task.text,
            steps=steps,
            total_steps=len(steps),
            total_estimated_minutes=time_available
        )
        
        # Update task with subtasks
        task.subtasks = subtasks
        task.subtasks_generated = True
        task.is_dummy = True
        
        self.session.add_thought("conclusion", f"[DUMMY] Created {len(steps)} subtasks")
        
        return breakdown


# Singleton instance
breakdown_agent = BreakdownAgent()

