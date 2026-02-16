"""
Task Suggester Agent

Specializes in matching tasks to user context:
- Considers time available
- Matches energy levels
- Accounts for emotional state
- Learns from past feedback
"""

import json
from typing import Optional

from app.models import Task, TaskSuggestion, UserContext, EnergyLevel, Subtask, SubtaskStatus
from app.services.tools import get_learning_insights
from app.logging_config import get_logger
from .base_agent import BaseAgent

logger = get_logger("TaskSuggester")

MAX_TIME_GAP = 2


def _is_eligible(task_minutes: int, available_minutes: int, task_energy: str, user_energy: str) -> bool:
    """Check if a task/subtask passes the hard eligibility rules."""
    if task_minutes > available_minutes:
        return False
    if (available_minutes - task_minutes) > MAX_TIME_GAP:
        return False
    if task_energy != user_energy:
        return False
    return True


class TaskSuggesterAgent(BaseAgent):
    """Agent that suggests the best task for the user's context."""
    
    AGENT_NAME = "TaskSuggester"
    
    SYSTEM_PROMPT = """IDENTITY & CORE RULES (Initialization)
You are the Task Suggester Agent for Karma, a productivity app. Your job is to select a task or subtask from the ELIGIBLE list provided to you.


CRITICAL CONSTRAINT: Any suggested task or subtask text must be UNDER 20 WORDS.

HARD CONSTRAINTS (non-negotiable, already enforced by pre-filter):
1. Exact energy match: task energy_required MUST equal user energy (low==low, medium==medium, high==high).
2. Time fit: estimated_minutes <= available_minutes.
3. Time-tightness: (available_minutes - estimated_minutes) <= 2. If gap > 2, task is ineligible.
4. If no eligible task/subtask exists, set suggest_quickwin=true, task_id=null. Do NOT rescope.

STYLE GUIDELINES:
- Direct & Disciplined: Use a direct tone. No sentimental framing or lifestyle-fluff.
- Immediately Executable: Tasks must be self-contained and finite.
- Bounded Outputs: Scope by numbers (e.g., "3 items") rather than ambiguity.

SELECTION LOGIC:
- You will ONLY receive tasks that already pass all hard constraints.
- Pick the single best match from the eligible list.
- If the eligible list is empty, set suggest_quickwin=true.


FEW-SHOT EXAMPLES:
available=10, energy=medium, task energy=low → INELIGIBLE (energy mismatch).
available=10, energy=medium, task energy=medium, est=7min (gap=3) → INELIGIBLE (gap > 2).
available=10, energy=medium, task energy=medium, est=9min (gap=1) → ELIGIBLE, pick it.
available=5, energy=low, task energy=low, est=5min (gap=0) → ELIGIBLE, pick it."""


    async def run(
        self,
        tasks: list[Task],
        context: UserContext,
        excluded_task_ids: list[str] = None,
        user_id: str = None
    ) -> Optional[TaskSuggestion]:
        """
        Suggest the best task for the user's context.
        """
        self._start_session()
        excluded_task_ids = excluded_task_ids or []
        available_minutes = context.time_available.value
        user_energy = context.energy_level.value
        
        available_tasks = [t for t in tasks if t.id not in excluded_task_ids]
        
        if not available_tasks:
            if self.session:
                self.session.add_thought(
                    "observation",
                    f"No tasks available after filtering (excluded {len(excluded_task_ids)} IDs)"
                )
            return None
        
        if self.session:
            self.session.add_thought("observation",
                f"Pre-filter: {len(available_tasks)} tasks, {available_minutes}min, {user_energy} energy, max gap={MAX_TIME_GAP}")

        eligible_tasks = []
        eligible_subtasks = []

        for t in available_tasks:
            t_energy = t.energy_required.value if t.energy_required else "unknown"
            t_minutes = t.estimated_minutes or 15

            if _is_eligible(t_minutes, available_minutes, t_energy, user_energy):
                eligible_tasks.append(t)

            if t.subtasks:
                for st in t.subtasks:
                    if st.status.value not in ("pending", "in_progress"):
                        continue
                    st_minutes = st.estimated_minutes or t_minutes
                    if _is_eligible(st_minutes, available_minutes, t_energy, user_energy):
                        eligible_subtasks.append((t, st))

        if self.session:
            self.session.add_thought("observation",
                f"Eligible: {len(eligible_tasks)} tasks, {len(eligible_subtasks)} subtasks")

        if not eligible_tasks and not eligible_subtasks:
            if self.session:
                self.session.add_thought("conclusion",
                    "No task/subtask passes hard constraints → QuickWin")
            logger.info(
                "TaskSuggester: no eligible tasks (available=%dmin, energy=%s, gap<=%d). Routing to QuickWin.",
                available_minutes, user_energy, MAX_TIME_GAP,
            )
            return None

        if self._is_dummy_mode():
            return self._dummy_suggest_from_eligible(eligible_tasks, eligible_subtasks, context)

        task_list_parts = []
        for t in eligible_tasks:
            task_info = f"- ID: {t.id}\n  Task: \"{t.text}\"\n  Est: {t.estimated_minutes}min, Energy: {t.energy_required.value if t.energy_required else 'unknown'}, Category: {t.category.value if t.category else 'unknown'}"
            task_list_parts.append(task_info)

        for t, st in eligible_subtasks:
            task_info = f"- Parent ID: {t.id}\n  Parent Task: \"{t.text}\"\n  Subtask: \"{st.instruction}\"\n  Subtask Est: {st.estimated_minutes}min, Energy: {t.energy_required.value if t.energy_required else 'unknown'}"
            task_list_parts.append(task_info)

        task_list = "\n".join(task_list_parts)

        emotional_context = f", Mood: {context.emotional_state.value}" if hasattr(context, 'emotional_state') and context.emotional_state else ""

        insights = get_learning_insights()
        learning_context = ""
        if insights.get("total_feedback", 0) > 0:
            learning_context = f"""
LEARNING FROM PAST:
- Acceptance rate: {insights.get('acceptance_rate', 0):.0%}
- Recent patterns: {insights.get('recent_patterns', 'No clear patterns yet')}
"""


        prompt = f"""Pick the single best task from this ELIGIBLE list.


USER CONTEXT:
- Available Time: {available_minutes} minutes
- Energy Level: {user_energy}{emotional_context}
{learning_context}

ELIGIBLE TASKS (all pass hard constraints):
{task_list}

Pick one. Return JSON:
{{
    "suggest_quickwin": false,
    "task_id": "<selected task ID>",
    "reasoning": "<1 sentence>",
    "confidence": <0.0-1.0>,
    "suggest_subtask": <true if picking a subtask>,
    "subtask_instruction": "<subtask instruction if suggest_subtask, else null>",
    "subtask_estimated_minutes": <subtask minutes if suggest_subtask, else null>,
    "is_rescoped": false

}}

JSON response:"""

        logger.info(
            "TaskSuggester LLM request: time_available=%s min, energy=%s. Eligible tasks sent to LLM:\n%s",
            available_minutes, user_energy, task_list,
        )
        logger.debug("TaskSuggester full LLM prompt:\n%s", prompt)

        try:
            response = await self._simple_completion(
                prompt,
                temperature=0.0,
                max_tokens=400,
                user_id=user_id,
                operation_type="suggest"
            )

            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                result = json.loads(response[json_start:json_end])

                if result.get("suggest_quickwin") is True:
                    logger.info(
                        "TaskSuggester LLM response (suggest_quickwin=true): %s",
                        json.dumps(result, indent=2),
                    )
                    if self.session:
                        self.session.add_thought("conclusion",
                            "LLM returned suggest_quickwin=true despite eligible list")
                    return None

                eligible_ids = set(t.id for t in eligible_tasks)
                eligible_ids.update(t.id for t, _ in eligible_subtasks)

                selected_task_id = result.get("task_id")
                if selected_task_id not in eligible_ids:
                    logger.warning(
                        "TaskSuggester LLM returned non-eligible task_id=%s. Routing to QuickWin.",
                        selected_task_id,
                    )
                    if self.session:
                        self.session.add_thought("conclusion",
                            f"LLM selected ineligible task {selected_task_id} → QuickWin")
                    return None

                selected_task = next(
                    (t for t in available_tasks if t.id == selected_task_id),
                    None
                )

                if selected_task:
                    suggest_subtask = result.get("suggest_subtask", False)
                    subtask_instruction = result.get("subtask_instruction")
                    subtask_minutes = result.get("subtask_estimated_minutes")

                    suggested_subtask = None
                    if suggest_subtask and subtask_instruction:
                        eligible_subtask_map = {
                            st.instruction: st for _, st in eligible_subtasks
                            if _.id == selected_task.id
                        }
                        pending_subtasks = [s for s in selected_task.subtasks if s.status.value in ("pending", "in_progress")]
                        matching_subtask = next(
                            (s for s in pending_subtasks
                             if s.instruction in eligible_subtask_map
                             and (subtask_instruction.lower() in s.instruction.lower()
                                  or s.instruction.lower() in subtask_instruction.lower())),
                            None
                        )
                        if matching_subtask:
                            suggested_subtask = matching_subtask
                        elif subtask_minutes and _is_eligible(subtask_minutes, available_minutes, selected_task.energy_required.value if selected_task.energy_required else user_energy, user_energy):
                            suggested_subtask = Subtask(
                                step_number=len(selected_task.subtasks) + 1,
                                instruction=subtask_instruction,
                                estimated_minutes=subtask_minutes,
                                status=SubtaskStatus.PENDING
                            )
                        else:
                            logger.warning(
                                "TaskSuggester LLM subtask fails constraints (est=%s, avail=%s). Ignoring subtask.",
                                subtask_minutes, available_minutes,
                            )
                            suggest_subtask = False
                            subtask_instruction = None
                            subtask_minutes = None

                    conclusion_text = f"Suggested: {selected_task.text}"
                    if suggest_subtask and subtask_instruction:
                        conclusion_text += f" - Subtask: {subtask_instruction}"

                    if self.session:
                        self.session.add_thought("conclusion", conclusion_text)

                    self._save_reasoning(
                        decision_type="suggestion",
                        input_context=f"Context: {available_minutes}min, {user_energy}",
                        conclusion=conclusion_text,
                        confidence=result.get("confidence", 0.7)
                    )

                    return TaskSuggestion(
                        task=selected_task,
                        reasoning=result.get("reasoning", "This task matches your current context."),
                        confidence_score=min(1.0, max(0.0, result.get("confidence", 0.7))),
                        suggested_subtask=suggested_subtask,
                        subtask_instruction=subtask_instruction if suggest_subtask else None,
                        subtask_estimated_minutes=subtask_minutes if suggest_subtask else None
                    )
                else:
                    raise ValueError(f"AI selected unknown task ID: {result.get('task_id')}")

        except json.JSONDecodeError as e:
            if self.session:
                self.session.add_thought("error", f"Failed to parse AI response: {e}")
            raise ValueError(f"Task suggestion failed: Invalid AI response")
        except Exception as e:
            if self.session:
                self.session.add_thought("error", f"Suggestion failed: {e}")
            raise ValueError(f"Task suggestion failed: {e}")

    def _dummy_suggest_from_eligible(
        self,
        eligible_tasks: list[Task],
        eligible_subtasks: list[tuple],
        context: UserContext
    ) -> Optional[TaskSuggestion]:
        """Dummy suggestion from pre-filtered eligible lists."""
        if self.session:
            self.session.add_thought("dummy_mode", "AI disabled - using dummy suggestion from eligible list")

        if eligible_subtasks:
            parent_task, subtask = eligible_subtasks[0]
            if self.session:
                self.session.add_thought("conclusion", f"[DUMMY] Selected subtask: {subtask.instruction}")
            return TaskSuggestion(
                task=parent_task,
                reasoning=f"[DUMMY MODE] Subtask matches time and energy. AI disabled.",
                confidence_score=0.5,
                suggested_subtask=subtask,
                subtask_instruction=subtask.instruction,
                subtask_estimated_minutes=subtask.estimated_minutes
            )

        if eligible_tasks:
            selected = eligible_tasks[0]
            selected.is_dummy = True
            if self.session:
                self.session.add_thought("conclusion", f"[DUMMY] Selected: {selected.text}")
            return TaskSuggestion(
                task=selected,
                reasoning=f"[DUMMY MODE] Task matches time and energy. AI disabled.",
                confidence_score=0.5
            )

        return None


# Singleton instance
task_suggester = TaskSuggesterAgent()
