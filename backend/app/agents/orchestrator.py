"""
Karma Orchestrator

The master agent that coordinates all specialized agents:
- Routes tasks to appropriate agents
- Manages the overall workflow
- Handles feedback and learning
"""

from datetime import datetime
from typing import Optional

from app.models import (
    Task, TaskSuggestion, TaskBreakdown, UserContext,
    EnergyLevel, EmotionalState, GENERIC_QUICKWIN_TASKS
)
from app.services.tools import (
    save_tasks, save_reasoning, record_user_feedback,
    get_learning_insights, save_task_with_details
)
from app.logging_config import get_ai_logger

from .task_analyzer import TaskAnalyzerAgent
from .task_suggester import TaskSuggesterAgent
from .task_enricher import TaskEnricherAgent
from .quickwin_agent import QuickWinAgent
from .breakdown_agent import BreakdownAgent

logger = get_ai_logger()


class KarmaOrchestrator:
    """
    Master orchestrator that coordinates all Karma agents.
    
    This is the main entry point for all agent operations.
    It decides which agent(s) to invoke and manages the workflow.
    """
    
    def __init__(self):
        # Initialize all agents
        self.analyzer = TaskAnalyzerAgent()
        self.suggester = TaskSuggesterAgent()
        self.enricher = TaskEnricherAgent()
        self.quickwin = QuickWinAgent()
        self.breakdown = BreakdownAgent()
        
        logger.info("Karma Orchestrator initialized with 5 specialized agents")
        logger.debug("  - TaskAnalyzer: Analyzes task properties")
        logger.debug("  - TaskSuggester: Matches tasks to context")
        logger.debug("  - TaskEnricher: Adds research & resources")
        logger.debug("  - QuickWin: Generates micro-tasks")
        logger.debug("  - Breakdown: Creates step-by-step plans")
    
    async def analyze_tasks(self, tasks: list[Task]) -> tuple[list[Task], dict]:
        """
        Analyze a list of tasks using the TaskAnalyzer agent.
        Also enriches each task using the TaskEnricher agent.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Tuple of (analyzed_tasks, reasoning_trace)
        """
        logger.info(f"Orchestrator: Analyzing {len(tasks)} tasks")
        
        analyzed_tasks = []
        all_reasoning = {
            "orchestrator": "KarmaOrchestrator",
            "operation": "analyze_tasks",
            "started_at": datetime.now().isoformat(),
            "agents_used": ["TaskAnalyzer", "TaskEnricher"],
            "task_traces": []
        }
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        for task in tasks:
            task_trace = {"task_id": task.id, "task_text": task.text}
            
            try:
                # Step 1: Analyze the task
                print(f"   📊 Analyzing: {task.text[:50]}...")
                analyzed_task = await self.analyzer.run(task)
                task_trace["analysis"] = "success"
                
                # Step 2: Enrich the task
                print(f"   📚 Enriching: {task.text[:50]}...")
                enrichment = await self.enricher.run(analyzed_task)
                analyzed_task.enrichment = enrichment
                
                # Update task with enrichment data
                if enrichment.get("category"):
                    from app.models import TaskCategory
                    try:
                        analyzed_task.category = TaskCategory(enrichment["category"])
                    except ValueError:
                        pass
                
                if enrichment.get("tags"):
                    analyzed_task.tags = enrichment["tags"]
                
                task_trace["enrichment"] = "success"
                
                # Save the fully analyzed and enriched task
                save_task_with_details(analyzed_task.model_dump(), today)
                
                analyzed_tasks.append(analyzed_task)
                
            except Exception as e:
                task_trace["error"] = str(e)
                print(f"   ❌ Failed: {e}")
                raise  # No fallbacks - fail fast
            
            all_reasoning["task_traces"].append(task_trace)
        
        # Save all tasks to date file
        save_tasks(analyzed_tasks, today)
        
        all_reasoning["completed_at"] = datetime.now().isoformat()
        all_reasoning["tasks_analyzed"] = len(analyzed_tasks)
        
        print(f"✅ Orchestrator: Analyzed {len(analyzed_tasks)} tasks")
        
        return analyzed_tasks, all_reasoning
    
    async def suggest_task(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str] = None
    ) -> tuple[Optional[TaskSuggestion], dict]:
        """
        Suggest a task using the TaskSuggester agent.
        
        Args:
            tasks: Available tasks
            context: User's current context
            excluded_task_ids: Tasks to exclude
            
        Returns:
            Tuple of (suggestion, reasoning_trace)
        """
        print(f"\n🎯 Orchestrator: Finding best task for {context.time_available.value}min, {context.energy_level.value} energy...")
        
        reasoning = {
            "orchestrator": "KarmaOrchestrator",
            "operation": "suggest_task",
            "context": {
                "time": context.time_available.value,
                "energy": context.energy_level.value,
                "mood": context.emotional_state.value if context.emotional_state else None
            },
            "agents_used": ["TaskSuggester"]
        }
        
        try:
            suggestion = await self.suggester.run(tasks, context, excluded_task_ids or [])
            
            if suggestion:
                reasoning["suggestion"] = {
                    "task_id": suggestion.task.id,
                    "task_text": suggestion.task.text,
                    "confidence": suggestion.confidence_score
                }
                print(f"✅ Orchestrator: Suggested '{suggestion.task.text}'")
            else:
                reasoning["suggestion"] = None
                print("⚠️ Orchestrator: No suitable task found")
            
            return suggestion, reasoning
            
        except Exception as e:
            reasoning["error"] = str(e)
            print(f"❌ Orchestrator: Suggestion failed - {e}")
            raise
    
    async def break_task_into_steps(
        self,
        task: Task,
        time_available: int
    ) -> tuple[TaskBreakdown, dict]:
        """
        Break a task into subtasks using the Breakdown agent.
        
        This generates subtasks with individual status tracking and time estimates.
        The subtasks are saved to the task for persistent tracking.
        
        Args:
            task: The task to break down
            time_available: Minutes available
            
        Returns:
            Tuple of (breakdown, reasoning_trace)
        """
        print(f"\n🎯 Orchestrator: Breaking down '{task.text[:40]}...' into subtasks...")
        
        reasoning = {
            "orchestrator": "KarmaOrchestrator",
            "operation": "break_task",
            "task_id": task.id,
            "time_available": time_available,
            "agents_used": ["Breakdown"]
        }
        
        try:
            breakdown = await self.breakdown.run(task, time_available)
            
            # The breakdown agent now also updates task.subtasks
            # Save the updated task with subtasks
            today = datetime.now().strftime("%Y-%m-%d")
            save_task_with_details(task.model_dump(), today)
            
            total_time = breakdown.total_estimated_minutes or sum(s.estimated_minutes or 5 for s in breakdown.steps)
            reasoning["steps_created"] = breakdown.total_steps
            reasoning["total_estimated_minutes"] = total_time
            print(f"✅ Orchestrator: Created {breakdown.total_steps} subtasks ({total_time} min total)")
            
            return breakdown, reasoning
            
        except Exception as e:
            reasoning["error"] = str(e)
            print(f"❌ Orchestrator: Breakdown failed - {e}")
            raise
    
    async def generate_quickwin(self, context: UserContext) -> dict:
        """
        Generate a quick win using the QuickWin agent.
        
        Args:
            context: User's current context
            
        Returns:
            Quick win dictionary
        """
        print(f"\n🎯 Orchestrator: Generating quick win for {context.energy_level.value} energy, {context.emotional_state.value if context.emotional_state else 'neutral'} mood...")
        
        try:
            quickwin = await self.quickwin.run(context)
            print(f"✅ Orchestrator: Generated '{quickwin['text'][:50]}...'")
            return quickwin
            
        except Exception as e:
            print(f"❌ Orchestrator: Quick win generation failed - {e}")
            raise
    
    async def enrich_task(self, task: Task) -> dict:
        """
        Enrich a single task using the TaskEnricher agent.
        
        Args:
            task: The task to enrich
            
        Returns:
            Enrichment dictionary
        """
        print(f"\n🎯 Orchestrator: Enriching '{task.text[:40]}...'")
        
        try:
            enrichment = await self.enricher.run(task)
            print(f"✅ Orchestrator: Added {len(enrichment.get('steps', []))} steps, {len(enrichment.get('suggested_resources', []))} resources")
            return enrichment
            
        except Exception as e:
            print(f"❌ Orchestrator: Enrichment failed - {e}")
            raise
    
    def record_feedback(
        self,
        task: Task,
        context: UserContext,
        accepted: bool,
        reasoning: str = ""
    ) -> dict:
        """
        Record user feedback for learning.
        
        Args:
            task: The task that was suggested
            context: User's context when suggestion was made
            accepted: Whether user accepted the task
            reasoning: The reasoning that was shown
            
        Returns:
            Feedback result
        """
        print(f"\n📝 Orchestrator: Recording feedback - {'Accepted' if accepted else 'Rejected'}: {task.text[:40]}...")
        
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
        
        # Save reasoning about the feedback
        save_reasoning(
            decision_type="orchestrator_feedback",
            input_context=f"User {'accepted' if accepted else 'rejected'}: {task.text}",
            reasoning_steps=[
                f"Task: {task.text}",
                f"Context: {context.time_available.value}min, {context.energy_level.value}",
                f"Decision: {'Accepted' if accepted else 'Rejected'}",
                f"Acceptance rate: {result.get('acceptance_rate', 0):.0%}"
            ],
            conclusion=f"Feedback recorded - {'proceeding to breakdown' if accepted else 'will avoid similar suggestions'}",
            confidence=1.0
        )
        
        return result
    
    def get_learning_insights(self) -> dict:
        """Get insights from accumulated feedback."""
        return get_learning_insights()


# Create the main orchestrator instance
karma_orchestrator = KarmaOrchestrator()

