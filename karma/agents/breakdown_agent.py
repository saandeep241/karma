"""
Breakdown Agent

Specializes in breaking tasks into actionable steps:
- Creates clear, specific steps
- Estimates time for each step
- Makes tasks less overwhelming
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Task, TaskStep, TaskBreakdown
from .base_agent import BaseAgent


class BreakdownAgent(BaseAgent):
    """Agent that breaks tasks into actionable steps."""
    
    AGENT_NAME = "Breakdown"
    
    SYSTEM_PROMPT = """You are the Breakdown Agent for Karma, a productivity app.

Your job is to break tasks into clear, actionable steps that eliminate decision paralysis.

Guidelines:
1. Each step should be SPECIFIC and immediately actionable
2. Steps should be small enough to feel achievable
3. First step should be the easiest to reduce friction
4. Include time estimates that sum to roughly the available time
5. Order steps logically

Bad step: "Work on the report"
Good step: "Open the report document and read the last paragraph you wrote"

Bad step: "Research the topic"  
Good step: "Google '[specific query]' and open the top 3 results"

Make each step so clear that there's no ambiguity about what to do."""

    async def run(self, task: Task, time_available: int) -> TaskBreakdown:
        """
        Break a task into actionable steps.
        
        Args:
            task: The task to break down
            time_available: Minutes available to work on this
            
        Returns:
            TaskBreakdown with steps
        """
        self._start_session()
        self.session.add_thought("observation", f"Breaking down: {task.text} ({time_available}min)")
        
        prompt = f"""Break this task into clear, actionable steps.

TASK: "{task.text}"
TIME AVAILABLE: {time_available} minutes

Create 3-6 specific steps that:
1. Are immediately actionable (no thinking required)
2. Are small enough to feel achievable
3. Have clear completion criteria
4. Sum to approximately {time_available} minutes

Return JSON:
{{
    "steps": [
        {{
            "step_number": 1,
            "instruction": "<specific action to take>",
            "estimated_minutes": <number>,
            "why": "<why this step is needed>"
        }},
        {{
            "step_number": 2,
            "instruction": "<specific action to take>",
            "estimated_minutes": <number>,
            "why": "<why this step is needed>"
        }}
    ],
    "total_time": <sum of all step times>,
    "breakdown_reasoning": "<brief explanation of your approach>"
}}

JSON response:"""

        try:
            response = self._simple_completion(prompt, temperature=0.5, max_tokens=800)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                breakdown_data = json.loads(response[json_start:json_end])
                
                steps = [
                    TaskStep(
                        step_number=s.get("step_number", i + 1),
                        instruction=s.get("instruction", "Complete this step"),
                        estimated_minutes=s.get("estimated_minutes")
                    )
                    for i, s in enumerate(breakdown_data.get("steps", []))
                ]
                
                if not steps:
                    raise ValueError("AI returned no steps")
                
                breakdown = TaskBreakdown(
                    task_id=task.id,
                    task_text=task.text,
                    steps=steps,
                    total_steps=len(steps)
                )
                
                self.session.add_thought("conclusion", f"Created {len(steps)} steps")
                
                self._save_reasoning(
                    decision_type="breakdown",
                    input_context=f"Task: {task.text}, Time: {time_available}min",
                    conclusion=f"Created {len(steps)} steps",
                    confidence=0.85
                )
                
                return breakdown
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task breakdown failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Breakdown failed: {e}")
            raise ValueError(f"Task breakdown failed: {e}")


# Singleton instance
breakdown_agent = BreakdownAgent()

