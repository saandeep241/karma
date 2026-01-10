# Karma Architecture Patterns Guide

This document explains the key architectural patterns used in the Karma app, with code examples and guidance on when to use each pattern.

---

## Table of Contents

1. [Orchestrator Pattern](#1-orchestrator-pattern)
2. [Agent Pattern](#2-agent-pattern)
3. [Tool Calling Pattern](#3-tool-calling-pattern)
4. [Session Pattern](#4-session-pattern)
5. [Persistence Pattern](#5-persistence-pattern)
6. [Learning Pattern](#6-learning-pattern)
7. [Reasoning Transparency Pattern](#7-reasoning-transparency-pattern)

---

## 1. Orchestrator Pattern

### What It Is

A central coordinator that routes requests to specialized agents and manages the overall workflow. The orchestrator doesn't do the work itself—it delegates to the right specialist.

### Code Example

```python
# agents/orchestrator.py
class KarmaOrchestrator:
    """Master orchestrator that coordinates all specialized agents."""
    
    def __init__(self):
        # Initialize all specialized agents
        self.analyzer = TaskAnalyzerAgent()
        self.suggester = TaskSuggesterAgent()
        self.enricher = TaskEnricherAgent()
        self.quickwin = QuickWinAgent()
        self.breakdown = BreakdownAgent()
    
    async def suggest_task(self, tasks, context, excluded_task_ids):
        """Route to the right agent for task suggestion."""
        # Orchestrator decides: use TaskSuggester
        suggestion = await self.suggester.run(tasks, context, excluded_task_ids)
        return suggestion, reasoning_trace
    
    async def analyze_tasks(self, tasks):
        """Coordinate multiple agents in sequence."""
        analyzed_tasks = []
        for task in tasks:
            # Step 1: Analyze
            analyzed_task = await self.analyzer.run(task)
            # Step 2: Enrich
            enrichment = await self.enricher.run(analyzed_task)
            analyzed_task.enrichment = enrichment
            analyzed_tasks.append(analyzed_task)
        return analyzed_tasks
```

### When to Use

✅ **Use Orchestrator Pattern when:**
- You have multiple specialized components that need coordination
- You want a single entry point for complex operations
- You need to chain multiple operations (analyze → enrich → suggest)
- You want to decouple API endpoints from specific implementations
- You need to manage cross-cutting concerns (logging, error handling)

❌ **Don't use when:**
- You have a single, simple operation (just call the function directly)
- The coordination logic is trivial (one function call)
- You're building a microservice (each service should be independent)

### Benefits

- **Single Responsibility**: Each agent does one thing well
- **Flexibility**: Easy to swap agents or add new ones
- **Testability**: Can test orchestrator and agents independently
- **Maintainability**: Changes to one agent don't affect others

### Real Example from Karma

```python
# main.py - API endpoint delegates to orchestrator
@app.post("/api/suggestion/from-storage")
async def get_suggestion_from_storage(request):
    # Load tasks
    all_tasks = load_tasks_from_storage()
    
    # Orchestrator handles the complexity
    suggestion, reasoning = await karma_orchestrator.suggest_task(
        tasks=all_tasks,
        context=context,
        excluded_task_ids=request.excluded_task_ids
    )
    
    return {"suggestion": suggestion}
```

---

## 2. Agent Pattern

### What It Is

Specialized components that encapsulate domain knowledge and reasoning. Each agent has a single responsibility and can reason about its domain using AI.

### Code Example

```python
# agents/base_agent.py
class BaseAgent(ABC):
    """Base class for all specialized agents."""
    
    AGENT_NAME = "BaseAgent"
    SYSTEM_PROMPT = "You are a helpful AI assistant."
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.session = None
    
    def _start_session(self):
        """Start tracking reasoning for this operation."""
        self.session = AgentSession(self.AGENT_NAME)
    
    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main entry point. Override in subclasses."""
        pass

# agents/task_analyzer.py
class TaskAnalyzerAgent(BaseAgent):
    """Specialized agent for analyzing task properties."""
    
    AGENT_NAME = "TaskAnalyzer"
    SYSTEM_PROMPT = """You are the Task Analyzer Agent.
    Your job is to analyze tasks and infer their properties:
    - Estimated duration
    - Energy requirements
    - Emotional fit
    - Category and tags"""
    
    async def run(self, task: Task) -> Task:
        """Analyze a single task."""
        self._start_session()
        self.session.add_thought("observation", f"Analyzing: {task.text}")
        
        # Build specialized prompt
        prompt = f"""Analyze this task: "{task.text}"
        Return JSON with estimated_minutes, energy_required, category..."""
        
        # Call AI with agent's specialized knowledge
        response = self._simple_completion(prompt)
        result = json.loads(response)
        
        # Populate task properties
        task.estimated_minutes = result["estimated_minutes"]
        task.energy_required = EnergyLevel(result["energy_required"])
        task.category = TaskCategory(result["category"])
        
        # Save reasoning
        self._save_reasoning("analysis", ...)
        
        return task
```

### When to Use

✅ **Use Agent Pattern when:**
- You need specialized reasoning for different domains
- Each domain has unique prompts/knowledge
- You want to track reasoning separately per domain
- You need to scale by adding more specialized agents
- Different operations require different AI strategies

❌ **Don't use when:**
- All operations are identical (use a single service)
- The specialization is trivial (just use functions)
- You don't need AI reasoning (use regular classes)

### Benefits

- **Domain Expertise**: Each agent is an expert in its domain
- **Separation of Concerns**: Task analysis vs suggestion vs breakdown
- **Reasoning Transparency**: Can see how each agent thinks
- **Extensibility**: Easy to add new agents (e.g., `PriorityAgent`, `DeadlineAgent`)

### Real Example from Karma

```python
# Five specialized agents:
# 1. TaskAnalyzerAgent - Analyzes task properties
# 2. TaskSuggesterAgent - Matches tasks to context
# 3. TaskEnricherAgent - Adds research and resources
# 4. BreakdownAgent - Creates step-by-step plans
# 5. QuickWinAgent - Generates micro-tasks

# Each has its own SYSTEM_PROMPT and run() method
```

---

## 3. Tool Calling Pattern

### What It Is

Agents can call external tools (functions) during their reasoning process. This enables agents to gather information, persist data, or interact with external systems.

### Code Example

```python
# agents/agent_tools.py
AGENT_TOOLS = {
    "search_web": {
        "function": search_web,
        "description": "Search the web for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "num_results": {"type": "integer"}
            }
        }
    },
    "check_weather": {
        "function": check_weather,
        "description": "Check weather conditions",
        "parameters": {...}
    }
}

def search_web(query: str, num_results: int = 5) -> dict:
    """Actual implementation of the tool."""
    # Use DuckDuckGo API
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    response = urllib.request.urlopen(url)
    data = json.loads(response.read())
    return {"results": data.get("RelatedTopics", [])}

# agents/base_agent.py
class BaseAgent:
    def _completion_with_tools(self, prompt, tools=None, max_iterations=5):
        """Execute AI completion with tool calling capability."""
        # Build tool definitions for OpenAI
        openai_tools = []
        for tool_name in tools:
            tool_def = AGENT_TOOLS[tool_name]
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_def["description"],
                    "parameters": tool_def["parameters"]
                }
            })
        
        messages = [{"role": "user", "content": prompt}]
        
        # Loop: AI can call tools multiple times
        while iterations < max_iterations:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto"  # Let AI decide when to use tools
            )
            
            if response.choices[0].message.tool_calls:
                # AI wants to call a tool
                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    result = execute_tool(tool_name, tool_args)
                    
                    # Add result back to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
            else:
                # AI has final answer
                return response.choices[0].message.content
```

### When to Use

✅ **Use Tool Calling Pattern when:**
- Agents need to gather external information (web search, APIs)
- Agents need to persist data during reasoning
- You want agents to make autonomous decisions about when to use tools
- You need to extend agent capabilities without changing agent code
- You want to track what tools agents use

❌ **Don't use when:**
- All operations are synchronous and don't need external data
- Tool calls are always required (just call the function directly)
- You don't need AI to decide when to use tools

### Benefits

- **Autonomy**: Agents decide when to use tools
- **Extensibility**: Add new tools without changing agent code
- **Transparency**: Can see what tools agents called
- **Flexibility**: Agents can call multiple tools in sequence

### Real Example from Karma

```python
# TaskEnricherAgent uses tools to research tasks
class TaskEnricherAgent(BaseAgent):
    async def run(self, task: Task):
        # Agent decides which tools to use
        tools_to_use = ["search_web", "search_for_steps"]
        
        if "outdoor" in task.text.lower():
            tools_to_use.append("check_weather")
        
        if "passport" in task.text.lower():
            tools_to_use.append("get_government_resources")
        
        # AI can call these tools during reasoning
        result = self._completion_with_tools(
            prompt=f"Enrich this task: {task.text}",
            tools=tools_to_use,
            max_iterations=6
        )
        
        # AI's response includes information from tool calls
        return parse_enrichment(result)
```

---

## 4. Session Pattern

### What It Is

Stateful sessions that track user interactions, reasoning chains, and context across multiple operations.

### Code Example

```python
# models.py
class Session(BaseModel):
    """User session tracking."""
    id: str
    todo_list: Optional[TodoList] = None
    context: Optional[UserContext] = None
    suggested_task_ids: list[str] = []  # Track what's been suggested
    current_task: Optional[Task] = None
    current_breakdown: Optional[TaskBreakdown] = None
    agent_reasoning: dict = {}  # Full reasoning trace
    current_reasoning: str = ""  # Latest reasoning step
    tool_calls: list[dict] = []  # Track tool calls
    feedback_history: list[dict] = []  # Track user feedback

# session_store.py
class SessionStore:
    """In-memory session storage."""
    
    def __init__(self):
        self._sessions: dict[str, Session] = {}
    
    def create_session(self) -> Session:
        """Create a new session."""
        session = Session()
        self._sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self._sessions.get(session_id)
    
    def update_session(self, session: Session):
        """Update existing session."""
        self._sessions[session.id] = session

# Usage in API
@app.post("/api/suggestion/get")
async def get_suggestion(request: GetSuggestionRequest):
    # Get existing session
    session = session_store.get_session(request.session_id)
    
    # Use session state
    excluded_ids = session.suggested_task_ids  # Avoid repeating suggestions
    
    # Get suggestion
    suggestion = await orchestrator.suggest_task(
        tasks=session.todo_list.tasks,
        context=session.context,
        excluded_task_ids=excluded_ids
    )
    
    # Update session
    session.suggested_task_ids.append(suggestion.task.id)
    session.current_task = suggestion.task
    session_store.update_session(session)
    
    return {"suggestion": suggestion}
```

### When to Use

✅ **Use Session Pattern when:**
- You need to track state across multiple API calls
- You want to remember what was suggested/rejected
- You need to maintain context (user preferences, current task)
- You want to track reasoning chains across operations
- You need to prevent duplicate operations (e.g., suggesting same task twice)

❌ **Don't use when:**
- Operations are stateless (each call is independent)
- You're using a database (sessions might be redundant)
- State is simple (just pass it as parameters)

### Benefits

- **State Management**: Centralized place for user state
- **Context Preservation**: Remember user preferences
- **Duplicate Prevention**: Track what's been done
- **Reasoning History**: See full reasoning chain

### Real Example from Karma

```python
# User flow with session:
# 1. Import tasks → session.todo_list = tasks
# 2. Set context → session.context = UserContext(...)
# 3. Get suggestion → session.suggested_task_ids.append(task_id)
# 4. Request alternative → uses excluded_task_ids to avoid repeats
# 5. Accept task → session.current_task = task, session.current_breakdown = breakdown
```

---

## 5. Persistence Pattern

### What It Is

File-based persistence using JSON files organized by date/type. Simple, human-readable storage without a database.

### Code Example

```python
# tools.py
DATA_DIR = Path(__file__).parent / "data"
TASKS_DIR = DATA_DIR / "tasks"
REASONING_DIR = DATA_DIR / "reasoning"
MEMORY_DIR = DATA_DIR / "memory"
TASK_DETAILS_DIR = DATA_DIR / "task_details"

def save_tasks(tasks: list, date: str) -> dict:
    """Save tasks to a date-based file."""
    filepath = TASKS_DIR / f"{date}.json"
    
    # Load existing tasks
    existing_data = {"tasks": []}
    if filepath.exists():
        with open(filepath, 'r') as f:
            existing_data = json.load(f)
    
    # Merge new tasks
    all_tasks = existing_data.get("tasks", [])
    all_tasks.extend([task.model_dump() for task in tasks])
    
    # Save
    data = {
        "date": date,
        "tasks": all_tasks,
        "updated_at": datetime.now().isoformat()
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return {"success": True, "filepath": str(filepath)}

def get_all_tasks_by_date() -> dict:
    """Load all tasks organized by date."""
    all_dates = {}
    
    for filepath in sorted(TASKS_DIR.glob("*.json")):
        if filepath.stem.startswith("20"):  # Date files
            with open(filepath, 'r') as f:
                data = json.load(f)
            all_dates[data["date"]] = data
    
    return all_dates

# Directory structure:
# data/
# ├── tasks/
# │   ├── 2026-01-10.json
# │   └── 2026-01-11.json
# ├── task_details/
# │   ├── {task_id}.json
# │   └── {task_id}_enrichment.json
# ├── reasoning/
# │   ├── 2026-01-10_11-34-17_TaskAnalyzer_analysis.json
# │   └── 2026-01-10_log.txt
# └── memory/
#     ├── feedback_history.json
#     └── rejected_tasks.json
```

### When to Use

✅ **Use Persistence Pattern when:**
- You want simple, human-readable storage
- You don't need complex queries (just load files)
- You want easy debugging (can read JSON files)
- Data volume is small-medium (not millions of records)
- You want version control friendly storage
- You're prototyping or building MVP

❌ **Don't use when:**
- You need complex queries (use a database)
- You have high write volume (file I/O is slower)
- You need transactions (file system doesn't support)
- You need concurrent writes (file locking issues)
- Data volume is very large (use a database)

### Benefits

- **Simplicity**: No database setup required
- **Readability**: Can inspect data directly
- **Portability**: Easy to backup/restore (just copy files)
- **Version Control**: Can track changes in git
- **No Dependencies**: No database server needed

### Real Example from Karma

```python
# Tasks organized by date
# data/tasks/2026-01-10.json contains all tasks for that day

# Individual task details
# data/task_details/{task_id}.json contains full task data
# data/task_details/{task_id}_enrichment.json contains AI enrichment

# Reasoning traces
# data/reasoning/2026-01-10_11-34-17_TaskAnalyzer_analysis.json
# data/reasoning/2026-01-10_log.txt (human-readable daily log)

# Learning/memory
# data/memory/feedback_history.json (all user feedback)
# data/memory/rejected_tasks.json (tasks rejected per context)
```

---

## 6. Learning Pattern

### What It Is

System learns from user feedback to improve future suggestions. Tracks accept/reject patterns and uses them to make better decisions.

### Code Example

```python
# tools.py
def record_user_feedback(
    task_text: str,
    accepted: bool,
    task_id: str,
    user_context: dict,
    reasoning_used: str
) -> dict:
    """Record user feedback for learning."""
    filepath = MEMORY_DIR / "feedback_history.json"
    
    # Load existing feedback
    history = []
    if filepath.exists():
        with open(filepath, 'r') as f:
            history = json.load(f)
    
    # Add new feedback
    feedback = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "task_text": task_text,
        "accepted": accepted,
        "user_context": user_context,  # time, energy, mood
        "reasoning_used": reasoning_used
    }
    history.append(feedback)
    
    # Save
    with open(filepath, 'w') as f:
        json.dump(history, f, indent=2)
    
    # Track rejections separately for quick lookup
    if not accepted:
        rejected_filepath = MEMORY_DIR / "rejected_tasks.json"
        rejected = {}
        if rejected_filepath.exists():
            with open(rejected_filepath, 'r') as f:
                rejected = json.load(f)
        
        # Key by context to track rejections per context
        context_key = f"{user_context['time_available']}_{user_context['energy_level']}"
        if context_key not in rejected:
            rejected[context_key] = []
        
        rejected[context_key].append({
            "task_id": task_id,
            "task_text": task_text,
            "rejected_at": datetime.now().isoformat()
        })
        
        with open(rejected_filepath, 'w') as f:
            json.dump(rejected, f, indent=2)
    
    return {
        "success": True,
        "total_feedback_count": len(history),
        "acceptance_rate": sum(1 for f in history if f["accepted"]) / len(history)
    }

def get_learning_insights(context_type: str = "all") -> dict:
    """Analyze past feedback to find patterns."""
    filepath = MEMORY_DIR / "feedback_history.json"
    
    with open(filepath, 'r') as f:
        history = json.load(f)
    
    insights = {
        "total_suggestions": len(history),
        "acceptance_rate": sum(1 for f in history if f["accepted"]) / len(history),
        "patterns": []
    }
    
    # Analyze patterns by energy level
    energy_stats = {}
    for f in history:
        energy = f["user_context"]["energy_level"]
        if energy not in energy_stats:
            energy_stats[energy] = {"total": 0, "accepted": 0}
        energy_stats[energy]["total"] += 1
        if f["accepted"]:
            energy_stats[energy]["accepted"] += 1
    
    for energy, stats in energy_stats.items():
        if stats["total"] >= 2:
            insights["patterns"].append({
                "type": "energy_level",
                "value": energy,
                "acceptance_rate": stats["accepted"] / stats["total"]
            })
    
    return insights

# Usage in agent
class TaskSuggesterAgent(BaseAgent):
    async def run(self, tasks, context, excluded_task_ids):
        # Get learning insights
        insights = get_learning_insights()
        
        # Include in prompt
        learning_context = f"""
        LEARNING FROM PAST:
        - Acceptance rate: {insights['acceptance_rate']:.0%}
        - Patterns: {insights['patterns']}
        """
        
        prompt = f"""Select the best task...
        {learning_context}
        """
        
        # AI uses insights to make better suggestions
        response = self._simple_completion(prompt)
        return parse_suggestion(response)
```

### When to Use

✅ **Use Learning Pattern when:**
- You want to improve suggestions over time
- You have user feedback (accept/reject, ratings)
- You want to personalize based on patterns
- You need to avoid repeating mistakes
- You want to track what works vs what doesn't

❌ **Don't use when:**
- Operations are deterministic (no learning needed)
- Feedback is not available
- Patterns are too complex to learn from simple feedback
- You need real-time learning (this is batch-based)

### Benefits

- **Continuous Improvement**: Gets better over time
- **Personalization**: Learns user preferences
- **Mistake Avoidance**: Doesn't repeat rejected suggestions
- **Transparency**: Can see what patterns were learned

### Real Example from Karma

```python
# User flow:
# 1. User gets suggestion → TaskSuggester uses learning insights
# 2. User rejects → record_user_feedback(accepted=False)
# 3. Task added to rejected_tasks.json for that context
# 4. Next suggestion → get_learning_insights() shows low acceptance for that context
# 5. AI adjusts suggestion strategy based on patterns
```

---

## 7. Reasoning Transparency Pattern

### What It Is

All agent reasoning is saved to files so you can see how decisions were made. Enables debugging, auditing, and understanding AI behavior.

### Code Example

```python
# agents/base_agent.py
class AgentSession:
    """Tracks reasoning chain for a single operation."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.thoughts: list[dict] = []
        self.tool_calls: list[dict] = []
    
    def add_thought(self, thought_type: str, content: str):
        """Add a thought to the reasoning chain."""
        self.thoughts.append({
            "type": thought_type,  # observation, reasoning, conclusion
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        print(f"🧠 [{self.agent_name}] {thought_type}: {content}")

# tools.py
def save_reasoning(
    decision_type: str,
    input_context: str,
    reasoning_steps: list[str],
    conclusion: str,
    confidence: float
) -> dict:
    """Save agent's reasoning process."""
    timestamp = datetime.now()
    
    # Save as JSON
    filename = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{decision_type}.json"
    filepath = REASONING_DIR / filename
    
    data = {
        "timestamp": timestamp.isoformat(),
        "decision_type": decision_type,
        "input_context": input_context,
        "reasoning_steps": reasoning_steps,
        "conclusion": conclusion,
        "confidence": confidence
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Also append to human-readable daily log
    daily_log = REASONING_DIR / f"{timestamp.strftime('%Y-%m-%d')}_log.txt"
    with open(daily_log, 'a') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"⏰ {timestamp.strftime('%H:%M:%S')} | {decision_type.upper()}\n")
        f.write(f"{'='*60}\n")
        f.write(f"📥 INPUT: {input_context}\n\n")
        f.write("🧠 REASONING:\n")
        for i, step in enumerate(reasoning_steps, 1):
            f.write(f"  {i}. {step}\n")
        f.write(f"\n✅ CONCLUSION: {conclusion}\n")
        f.write(f"📊 CONFIDENCE: {confidence:.0%}\n")
    
    return {"success": True, "filepath": str(filepath)}

# Usage in agent
class TaskSuggesterAgent(BaseAgent):
    async def run(self, tasks, context, excluded_task_ids):
        self._start_session()
        
        # Track reasoning
        self.session.add_thought("observation", f"Selecting from {len(tasks)} tasks")
        self.session.add_thought("reasoning", "Considering time and energy match")
        
        # ... make decision ...
        
        # Save reasoning
        self._save_reasoning(
            decision_type="suggestion",
            input_context=f"Context: {context.time_available.value}min",
            reasoning_steps=self.session.get_reasoning_chain(),
            conclusion=f"Suggested: {selected_task.text}",
            confidence=0.85
        )
```

### When to Use

✅ **Use Reasoning Transparency Pattern when:**
- You need to debug AI decisions
- You want to audit what the system did
- You need to explain decisions to users
- You're building trust (show how decisions are made)
- You want to improve prompts based on actual reasoning
- Regulatory/compliance requires explainability

❌ **Don't use when:**
- Operations are too simple (no reasoning needed)
- Performance is critical (logging adds overhead)
- Reasoning is not important for your use case

### Benefits

- **Debugging**: See exactly how decisions were made
- **Trust**: Users can see the reasoning
- **Improvement**: Learn from actual reasoning to improve prompts
- **Auditing**: Full history of all decisions
- **Transparency**: No black box

### Real Example from Karma

```python
# Files created:
# data/reasoning/2026-01-10_11-34-17_TaskAnalyzer_analysis.json
# data/reasoning/2026-01-10_11-35-55_TaskSuggester_suggestion.json
# data/reasoning/2026-01-10_log.txt (human-readable daily log)

# Example log entry:
# ============================================================
# ⏰ 11:35:55 | TASKSUGGESTER_SUGGESTION
# ============================================================
# 📥 INPUT: Context: 30min, medium
# 
# 🧠 REASONING:
#   1. [observation] Selecting from 5 tasks for 30min, medium energy
#   2. [reasoning] Task A fits time but requires high energy
#   3. [reasoning] Task B matches both time and energy
#   4. [conclusion] Selected: Task B
# 
# ✅ CONCLUSION: Suggested: "Review project proposal"
# 📊 CONFIDENCE: 85%
```

---

## Pattern Combinations

These patterns work well together:

### Orchestrator + Agent Pattern
- Orchestrator coordinates multiple specialized agents
- Each agent handles its domain

### Agent + Tool Calling Pattern
- Agents use tools to gather information
- Tools extend agent capabilities

### Session + Learning Pattern
- Session tracks what's been suggested
- Learning uses feedback to improve

### Persistence + Reasoning Transparency
- Save reasoning to files
- Can review decisions later

---

## Summary

| Pattern | Use When | Key Benefit |
|---------|----------|-------------|
| **Orchestrator** | Multiple components need coordination | Single entry point, flexible routing |
| **Agent** | Specialized reasoning per domain | Domain expertise, separation of concerns |
| **Tool Calling** | Agents need external capabilities | Autonomy, extensibility |
| **Session** | Stateful operations across calls | Context preservation, duplicate prevention |
| **Persistence** | Simple storage without database | Readability, portability |
| **Learning** | User feedback available | Continuous improvement |
| **Reasoning Transparency** | Need to debug/audit decisions | Trust, explainability |

---

## Next Steps

1. **Identify your use case**: Which patterns apply?
2. **Start simple**: Don't use all patterns at once
3. **Iterate**: Add patterns as needed
4. **Learn from Karma**: See how patterns are combined in practice

For questions or contributions, see the main README.md
