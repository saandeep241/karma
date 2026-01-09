"""
Karma Agents - Multi-Agent Architecture

Each agent is specialized for a specific task:
- TaskAnalyzerAgent: Analyzes tasks to infer properties
- TaskSuggesterAgent: Suggests the best task for user's context
- TaskEnricherAgent: Enriches tasks with research and resources (uses web tools!)
- QuickWinAgent: Generates personalized quick wins
- BreakdownAgent: Breaks tasks into actionable steps
- KarmaOrchestrator: Coordinates all agents

Tools available to agents:
- search_web: Search the internet for information
- search_for_steps: Find step-by-step guides
- check_weather: Get current weather conditions
- get_government_resources: Find official government resources
"""

from .base_agent import BaseAgent
from .task_analyzer import TaskAnalyzerAgent
from .task_suggester import TaskSuggesterAgent
from .task_enricher import TaskEnricherAgent
from .quickwin_agent import QuickWinAgent
from .breakdown_agent import BreakdownAgent
from .orchestrator import KarmaOrchestrator

# Main orchestrator instance
karma_orchestrator = KarmaOrchestrator()

__all__ = [
    "BaseAgent",
    "TaskAnalyzerAgent",
    "TaskSuggesterAgent", 
    "TaskEnricherAgent",
    "QuickWinAgent",
    "BreakdownAgent",
    "KarmaOrchestrator",
    "karma_orchestrator"
]

