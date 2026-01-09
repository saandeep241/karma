"""
Task Analyzer Agent

Specializes in analyzing tasks to infer their properties:
- Estimated duration
- Energy requirements
- Emotional fit
- Category and tags
"""

import json
import sys
from typing import Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Task, EnergyLevel, EmotionalState, TaskCategory
from .base_agent import BaseAgent


class TaskAnalyzerAgent(BaseAgent):
    """Agent that analyzes tasks to understand their properties."""
    
    AGENT_NAME = "TaskAnalyzer"
    
    SYSTEM_PROMPT = """You are the Task Analyzer Agent for Karma, a productivity app.

Your job is to analyze tasks and infer their properties:
1. **Estimated Time**: How long will this task realistically take?
2. **Energy Required**: Low (mindless), Medium (focused), or High (creative/complex)
3. **Emotional Fit**: What moods suit this task? (stressed, anxious, calm, happy, tired, motivated, neutral, sleepy, focused, creative, bored)
4. **Category**: work, personal, health, finance, learning, social, home, errands, creative, admin, other
5. **Tags**: 2-4 relevant keywords

Be realistic and specific. A "quick email" is 5 minutes, but "write a report" is 30-60 minutes.
Always return valid JSON."""

    async def run(self, task: Task) -> Task:
        """
        Analyze a single task and populate its properties.
        
        Args:
            task: The task to analyze
            
        Returns:
            The task with populated properties
        """
        self._start_session()
        self.session.add_thought("observation", f"Analyzing task: {task.text}")
        
        prompt = f"""Analyze this task and estimate its properties.

TASK: "{task.text}"

Return a JSON object with:
{{
    "estimated_minutes": <integer: 5, 10, 15, 30, or 60>,
    "energy_required": "<low|medium|high>",
    "emotional_fit": ["<mood1>", "<mood2>"],
    "category": "<category>",
    "tags": ["<tag1>", "<tag2>"],
    "task_type": "<brief description of task type>",
    "reasoning": "<why you made these estimates>"
}}

JSON response:"""

        try:
            response = self._simple_completion(prompt, temperature=0.3, max_tokens=400)
            
            # Parse JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                
                # Populate task properties
                task.estimated_minutes = result.get("estimated_minutes", 15)
                
                energy = result.get("energy_required", "medium").lower()
                if energy in ["low", "medium", "high"]:
                    task.energy_required = EnergyLevel(energy)
                
                emotional_fit = result.get("emotional_fit", ["neutral"])
                task.emotional_fit = [
                    EmotionalState(e) for e in emotional_fit
                    if e in [es.value for es in EmotionalState]
                ]
                
                category = result.get("category", "other").lower()
                if category in [c.value for c in TaskCategory]:
                    task.category = TaskCategory(category)
                else:
                    task.category = TaskCategory.OTHER
                
                task.tags = result.get("tags", [])
                task.task_type = result.get("task_type", "general")
                task.ai_reasoning = result.get("reasoning", "")
                
                self.session.add_thought("conclusion", 
                    f"Analyzed: {task.estimated_minutes}min, {task.energy_required.value} energy, {task.category.value}")
                
                self._save_reasoning(
                    decision_type="analysis",
                    input_context=f"Task: {task.text}",
                    conclusion=f"{task.estimated_minutes}min, {task.energy_required.value}, {task.category.value}",
                    confidence=0.85
                )
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task analysis failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Analysis failed: {e}")
            raise ValueError(f"Task analysis failed: {e}")
        
        return task
    
    async def run_batch(self, tasks: list[Task]) -> list[Task]:
        """
        Analyze multiple tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List of analyzed tasks
        """
        analyzed = []
        for task in tasks:
            try:
                analyzed_task = await self.run(task)
                analyzed.append(analyzed_task)
            except Exception as e:
                print(f"⚠️ [{self.AGENT_NAME}] Failed to analyze '{task.text}': {e}")
                # Re-raise to fail fast (no fallbacks)
                raise
        return analyzed


# Singleton instance
task_analyzer = TaskAnalyzerAgent()

