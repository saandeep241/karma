"""
Task Analyzer Agent

Specializes in analyzing tasks to infer their properties:
- Estimated duration
- Energy requirements
- Emotional fit
- Category and tags
"""

import json

from app.models import Task, EnergyLevel, EmotionalState, TaskCategory
from .base_agent import BaseAgent


class TaskAnalyzerAgent(BaseAgent):
    """Agent that analyzes tasks to understand their properties."""
    
    AGENT_NAME = "TaskAnalyzer"
    
    SYSTEM_PROMPT = """You are the Task Analyzer Agent for Karma, a productivity app.

Your job is to analyze tasks and infer their properties:
1. **Estimated Time**: How long will this task realistically take?
2. **Energy Required**: Low (mindless), Medium (focused), or High (creative/complex)
3. **Emotional Fit**: What moods suit this task? (stressed, anxious, calm, happy, tired, motivated, neutral, sleepy, focused, creative, bored)
4. **Category**: Must be exactly one of: work, personal, health, finance, learning, social, home, errands, creative, admin, other (use "creative" not "creativity")
5. **Tags**: 2-4 relevant keywords

Be realistic and specific. A "quick email" is 5 minutes, but "write a report" is 30-60 minutes.
Always return valid JSON."""

    async def run(self, task: Task, user_id: str = None) -> Task:
        """
        Analyze a single task and populate its properties.
        
        Args:
            task: The task to analyze
            user_id: User ID for token usage tracking
            
        Returns:
            The task with populated properties
        """
        self._start_session()
        self.session.add_thought("observation", f"Analyzing task: {task.text}")
        
        # Check if in dummy mode
        if self._is_dummy_mode():
            return self._dummy_analyze(task)
        
        prompt = f"""Analyze this task and estimate its properties.

TASK: "{task.text}"

Return a JSON object with:
{{
    "estimated_minutes": <integer: 5, 10, 15, 30, or 60>,
    "energy_required": "<low|medium|high>",
    "emotional_fit": ["<mood1>", "<mood2>"],
    "category": "<exactly one of: work|personal|health|finance|learning|social|home|errands|creative|admin|other>",
    "tags": ["<tag1>", "<tag2>"],
    "task_type": "<brief description of task type>",
    "reasoning": "<why you made these estimates>"
}}

Use the exact category value (e.g. "creative" not "creativity"). JSON response:"""

        try:
            response = await self._simple_completion(
                prompt, 
                temperature=0.3, 
                max_tokens=400,
                user_id=user_id,
                task_id=task.id,
                operation_type="analyze"
            )
            
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
                
                from app.models import normalize_task_category
                category = result.get("category", "other")
                task.category = normalize_task_category(category)
                
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
    
    def _dummy_analyze(self, task: Task) -> Task:
        """Generate dummy analysis when AI is not enabled."""
        self.session.add_thought("dummy_mode", "AI disabled - using dummy analysis")
        
        # Simple heuristics for dummy mode
        text_lower = task.text.lower()
        
        # Estimate time based on keywords
        if any(w in text_lower for w in ["quick", "simple", "check", "reply"]):
            task.estimated_minutes = 5
        elif any(w in text_lower for w in ["review", "read", "call", "email"]):
            task.estimated_minutes = 15
        elif any(w in text_lower for w in ["write", "create", "build", "develop"]):
            task.estimated_minutes = 30
        else:
            task.estimated_minutes = 15
        
        # Estimate energy
        if any(w in text_lower for w in ["organize", "clean", "file", "sort"]):
            task.energy_required = EnergyLevel.LOW
        elif any(w in text_lower for w in ["create", "design", "write", "develop", "build"]):
            task.energy_required = EnergyLevel.HIGH
        else:
            task.energy_required = EnergyLevel.MEDIUM
        
        # Guess category
        if any(w in text_lower for w in ["work", "meeting", "report", "project", "client"]):
            task.category = TaskCategory.WORK
        elif any(w in text_lower for w in ["exercise", "gym", "run", "health", "doctor"]):
            task.category = TaskCategory.HEALTH
        elif any(w in text_lower for w in ["buy", "shop", "store", "pick up"]):
            task.category = TaskCategory.ERRANDS
        elif any(w in text_lower for w in ["learn", "study", "course", "read"]):
            task.category = TaskCategory.LEARNING
        else:
            task.category = TaskCategory.PERSONAL
        
        task.emotional_fit = [EmotionalState.NEUTRAL]
        task.tags = []
        task.task_type = "general"
        task.ai_reasoning = None
        task.is_dummy = True
        
        self.session.add_thought("conclusion", 
            f"Analyzed: {task.estimated_minutes}min, {task.energy_required.value} energy, {task.category.value}")
        
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

