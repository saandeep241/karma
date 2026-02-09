"""
Task Enricher Agent (Add Task Agent)

Specializes in enriching tasks with additional context by:
- Searching the web for task-specific information
- Checking weather for outdoor activities
- Finding official resources for government tasks
- Generating intelligent subtasks based on research
"""

import json
from datetime import datetime

from app.models import Task
from app.services.tools import TASK_DETAILS_DIR
from .base_agent import BaseAgent


class TaskEnricherAgent(BaseAgent):
    """Agent that enriches tasks with research, questions, and resources using web tools."""
    
    AGENT_NAME = "TaskEnricher"
    
    SYSTEM_PROMPT = """You are the Task Enricher Agent for Karma, a productivity app.

When a user adds a new task, you MUST use the available tools to research and enrich it:

AVAILABLE TOOLS:
1. **search_web**: Search the internet for information about the task
2. **search_for_steps**: Find step-by-step guides for completing the task
3. **check_weather**: Check weather conditions (for outdoor tasks)
4. **get_government_resources**: Find official government resources (for passport, visa, taxes, etc.)

YOUR PROCESS:
1. Analyze the task to understand what it involves
2. ALWAYS call relevant tools to gather real information:
   - For ANY task: call search_web to find current information
   - For government/official tasks: call get_government_resources
   - For outdoor activities: call check_weather
   - For complex tasks: call search_for_steps
3. Use the tool results to provide SPECIFIC, ACCURATE information

IMPORTANT: 
- Do NOT make up information - use the tools to find real data
- Include actual URLs and resources from your searches
- Provide specific steps based on what you find
- If a task is technical or domain-specific, search for it first

After using tools, return JSON with your findings."""

    async def run(self, task: Task, user_id: str = None) -> dict:
        """
        Enrich a task with additional context and resources using web tools.
        
        Args:
            task: The task to enrich
            user_id: User ID for token usage tracking
            
        Returns:
            Dictionary with enrichment data
        """
        self._start_session()
        self.session.add_thought("observation", f"Enriching task: {task.text} (ID: {task.id})")
        
        # Check if in dummy mode
        if self._is_dummy_mode():
            return self._dummy_enrich(task)
        
        # Determine what tools to use based on task content
        task_lower = task.text.lower()
        tools_to_use = ["search_web", "search_for_steps"]  # Always use these
        
        # Add weather tool for outdoor tasks
        outdoor_keywords = ["outside", "outdoor", "walk", "run", "jog", "hike", "bike", "garden", "park", "beach", "picnic", "sports", "exercise outdoor"]
        if any(kw in task_lower for kw in outdoor_keywords):
            tools_to_use.append("check_weather")
            self.session.add_thought("reasoning", "Task involves outdoor activity - will check weather")
        
        # Add government resources for official tasks
        gov_keywords = ["passport", "visa", "license", "permit", "tax", "immigration", "ssn", "social security", "dmv", "registration", "citizenship", "green card"]
        if any(kw in task_lower for kw in gov_keywords):
            tools_to_use.append("get_government_resources")
            self.session.add_thought("reasoning", "Task involves official/government process - will find official resources")
        
        prompt = f"""Enrich this task with helpful information by using your tools.

TASK: "{task.text}"
TASK ID: "{task.id}"

INSTRUCTIONS:
1. First, use search_web to find current information about this task
2. Use search_for_steps to find a step-by-step guide
3. If this involves outdoor activities, use check_weather
4. If this involves government/official processes, use get_government_resources

After gathering information from tools, provide a comprehensive enrichment.

Return JSON with this structure:
{{
    "estimated_minutes": <realistic time based on your research>,
    "steps": [
        "Step 1: <specific action based on research>",
        "Step 2: <specific action>",
        ...
    ],
    "probable_questions": [
        "<question based on what you learned>",
        ...
    ],
    "suggested_resources": [
        "<actual URL or specific resource from your search>",
        ...
    ],
    "potential_blockers": [
        "<real obstacle based on research>",
        ...
    ],
    "success_criteria": [
        "<how to know it's done>",
        ...
    ],
    "category": "<exactly one of: work|personal|health|finance|learning|social|home|errands|creative|admin|other - use 'creative' not 'creativity'>",
    "tags": ["<tag1>", "<tag2>"],
    "weather_info": "<if outdoor task, include weather recommendation>",
    "official_resources": "<if government task, include official URLs>",
    "agent_notes": "<summary of what you found and key tips>"
}}

Use the tools now to research this task, then provide your JSON response."""

        try:
            # Use tool calling to research the task
            result = await self._completion_with_tools(
                prompt=prompt,
                tools=tools_to_use,
                temperature=0.6,
                max_tokens=2000,
                max_iterations=6,
                user_id=user_id,
                task_id=task.id,
                operation_type="enrich"
            )
            
            response_text = result.get("response", "")
            tool_results = result.get("tool_results", [])
            
            self.session.add_thought("observation", f"Made {len(tool_results)} tool calls")
            
            # Parse JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                enrichment_data = json.loads(response_text[json_start:json_end])
                
                # Build enrichment object
                enrichment = {
                    "task_id": task.id,
                    "task_text": task.text,
                    "enriched_at": datetime.now().isoformat(),
                    "enriched_by": self.AGENT_NAME,
                    "tools_used": [tc["tool"] for tc in result.get("tool_calls", [])],
                    "estimated_minutes": enrichment_data.get("estimated_minutes", 30),
                    "steps": enrichment_data.get("steps", []),
                    "probable_questions": enrichment_data.get("probable_questions", []),
                    "suggested_resources": enrichment_data.get("suggested_resources", []),
                    "potential_blockers": enrichment_data.get("potential_blockers", []),
                    "success_criteria": enrichment_data.get("success_criteria", []),
                    "category": enrichment_data.get("category", "other"),
                    "tags": enrichment_data.get("tags", []),
                    "weather_info": enrichment_data.get("weather_info"),
                    "official_resources": enrichment_data.get("official_resources"),
                    "agent_notes": enrichment_data.get("agent_notes", ""),
                    "raw_tool_results": tool_results  # Store raw results for reference
                }
                
                # Save enrichment to file
                self._save_enrichment(task.id, enrichment)
                
                self.session.add_thought("conclusion", 
                    f"Enriched with {len(enrichment['steps'])} steps, {len(enrichment['suggested_resources'])} resources from {len(tool_results)} tool calls")
                
                self._save_reasoning(
                    decision_type="enrichment",
                    input_context=f"Task: {task.text}",
                    conclusion=f"Added {len(enrichment['steps'])} steps, {len(enrichment['suggested_resources'])} resources using {len(tool_results)} tool calls",
                    confidence=0.9
                )
                
                return enrichment
            else:
                raise ValueError("AI did not return valid JSON")
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task enrichment failed: Invalid AI response")
        except Exception as e:
            self.session.add_thought("error", f"Enrichment failed: {e}")
            raise ValueError(f"Task enrichment failed: {e}")
    
    def _save_enrichment(self, task_id: str, enrichment: dict):
        """Save enrichment data to a file."""
        TASK_DETAILS_DIR.mkdir(parents=True, exist_ok=True)
        filepath = TASK_DETAILS_DIR / f"{task_id}_enrichment.json"
        
        # Don't save raw tool results to file (too large)
        enrichment_to_save = {k: v for k, v in enrichment.items() if k != "raw_tool_results"}
        
        with open(filepath, 'w') as f:
            json.dump(enrichment_to_save, f, indent=2)
        
        print(f"📝 [{self.AGENT_NAME}] Saved enrichment to {filepath}")
    
    def _dummy_enrich(self, task: Task) -> dict:
        """Generate dummy enrichment when AI is not enabled."""
        self.session.add_thought("dummy_mode", "AI disabled - using dummy enrichment")
        
        enrichment = {
            "task_id": task.id,
            "task_text": task.text,
            "enriched_at": datetime.now().isoformat(),
            "enriched_by": self.AGENT_NAME,
            "tools_used": [],
            "estimated_minutes": 15,
            "steps": [
                "Step 1: Get started with the task",
                "Step 2: Work on the main part",
                "Step 3: Review and finish"
            ],
            "probable_questions": [
                "What resources do I need?",
                "How long will this take?"
            ],
            "suggested_resources": [],
            "potential_blockers": [],
            "success_criteria": [
                "Task is completed"
            ],
            "category": "other",
            "tags": [],
            "agent_notes": None,
            "is_dummy": True
        }
        
        # Save enrichment
        self._save_enrichment(task.id, enrichment)
        
        self.session.add_thought("conclusion", "Created basic enrichment")
        
        return enrichment


# Singleton instance
task_enricher = TaskEnricherAgent()

