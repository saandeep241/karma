# Plan: Remove Overwhelmed/Low Energy from UI and emotional_state from Backend

## Summary

1. **UI**: Remove "Overwhelmed" and "Low Energy" mood options; keep only Enthusiastic, Neutral, Tired. Stop sending `emotional_state` to the API; send only `energy_level` (derived from the remaining 3 moods).
2. **Backend**: Remove user-facing `emotional_state` from context everywhere. Keep `EmotionalState` enum and `Task.emotional_fit` for now (task-level “which moods suit this task”); they are unused in filtering after this change and can be removed in a later cleanup if desired.

---

## Part 1: Frontend (UI) changes

### 1.1 `frontend/src/components/FocusMode.tsx`

| Change | Details |
|--------|---------|
| **Mood type and options** | Update `Mood` to `'enthusiastic' \| 'neutral' \| 'tired'`. Remove `overwhelmed` and `low_energy` from `MOODS` (so the array has 3 items). |
| **Remove emotional_state mapping** | Delete `mapMoodToBackendEmotionalState`. |
| **Energy level only** | In `fetchSuggestion`, set `energyLevel` from mood only: `enthusiastic` → `'high'`, `tired` → `'low'`, `neutral` → `'medium'`. Do **not** call the backend with `emotional_state`. |
| **API request** | In `api.getStoredSuggestion({...})`, remove the `emotional_state` property. |
| **Fallback quickwin** | In the fallback/error paths that call `api.getQuickWin(...)`, remove the second argument (mood/emotional_state) if the API is updated to not accept it; otherwise keep for backward compatibility until backend is updated. |
| **Layout** | `MOODS.slice(0, 3)` and `MOODS.slice(3)`: after removing 2 items, you have 3 moods. Use a single row or adjust to `MOODS.slice(0, 3)` only and remove the second row (or keep one row of 3). Remove the `m.value === 'overwhelmed'` SVG branch; use a single icon for `tired` in the remaining options. |

### 1.2 `frontend/src/api/client.ts`

| Change | Details |
|--------|---------|
| **getStoredSuggestion request type** | Remove `emotional_state?: string` from the request body type. |

---

## Part 2: Backend model changes

### 2.1 `backend/app/models.py`

| Change | Details |
|--------|---------|
| **UserContext** | Remove field `emotional_state: Optional[EmotionalState] = None`. |
| **SetContextRequest** | Remove field `emotional_state: Optional[EmotionalState] = None`. |
| **SuggestFromStorageRequest** | Remove field `emotional_state: Optional[str] = None`. |
| **EmotionalState enum** | **Keep** for now (used by `Task.emotional_fit` and task_analyzer). Optional follow-up: remove `Task.emotional_fit` and `EmotionalState` in a later change. |

---

## Part 3: Backend route changes

### 3.1 `backend/app/routes/suggestions.py`

| Change | Details |
|--------|---------|
| **get_suggestion_from_storage** | Do not build `emotional_state` from the request. Create `UserContext` with only `time_available` and `energy_level`. Remove `EmotionalState` from imports if no longer used here. |
| **_generate_quickwin** | Stop reading `mood` from the request. Build `UserContext` with only `time_available` and `energy_level`; do not set `emotional_state`. |
| **get_options** | Remove `emotional_options` from the response (or leave as empty array during transition). Remove `EmotionalState` from imports if unused. |

### 3.2 `backend/app/routes/sessions.py`

| Change | Details |
|--------|---------|
| **set_user_context** | Remove `emotional_state` from `SetContextRequest` usage. Build `UserContext` with only `time_available` and `energy_level`. Remove `emotional_state` from the returned `context` object. Remove `EmotionalState` from imports if unused. |

---

## Part 4: Backend agent changes

### 4.1 `backend/app/agents/task_suggester.py`

| Change | Details |
|--------|---------|
| **Prompts** | Remove any line or phrase that refers to “mood” or “emotional state” in the user context (e.g. “Match task mood to user's emotional state”). |
| **Context string** | Remove `emotional_context = f", Mood: {context.emotional_state.value}"` and any concatenation of it. Pass only time and energy in the USER CONTEXT section (e.g. “Available Time”, “Energy Level”). |

### 4.2 `backend/app/agents/quickwin_agent.py`

| Change | Details |
|--------|---------|
| **Observation** | Stop using `context.emotional_state`. Remove `mood = context.emotional_state.value if context.emotional_state else "neutral"` and any thought/log that includes “mood”. |
| **Prompt** | Remove “Current Mood” and mood-based guidance from the prompt. Rely only on “Available Time” and “Energy Level” (and existing energy_guidance). Remove or simplify `mood_guidance` usage (e.g. remove the line “Current Mood: {mood} → …”). |
| **save_reasoning / input_context** | Remove `mood` from the context string passed to `input_context`. |

### 4.3 `backend/app/agents/orchestrator.py`

| Change | Details |
|--------|---------|
| **suggest_task reasoning** | In the `reasoning` dict, remove the `"mood"` key (or any `context.emotional_state`). |
| **generate_quickwin print** | Remove “, context.emotional_state... mood” from the print statement. |
| **record_feedback** | In `user_context` passed to `record_user_feedback`, remove `"emotional_state": context.emotional_state.value if context.emotional_state else None`. |
| **Imports** | Remove `EmotionalState` from imports if no longer used. |

---

## Part 5: Backend services and database

### 5.1 `backend/app/services/tools.py`

| Change | Details |
|--------|---------|
| **record_user_feedback** | No signature change. Callers will simply omit `emotional_state` from `user_context`. Optional: document that `user_context` may contain only `time_available` and `energy_level`. |
| **get_learning_insights** | If it aggregates or displays emotional_state/mood from feedback, remove that so insights use only time_available and energy_level. |
| **Serialization** | Keep `EmotionalState` in `isinstance(...)` for serializing `Task.emotional_fit` if that remains. |

### 5.2 `backend/app/database/repository.py`

| Change | Details |
|--------|---------|
| **record_feedback** | Stop setting `context_mood` from context, or use `context.get("emotional_state")` then `context.get("mood")` for backward compatibility with existing data; then pass `None` for new feedback. Prefer: set `context_mood=context.get("emotional_state") or context.get("mood")` so existing code paths stay valid; after orchestrator stops sending emotional_state, this will store `None`. No schema change required. |

### 5.3 `backend/app/database/models.py`

| Change | Details |
|--------|---------|
| **FeedbackModel** | Leave `context_mood` as optional (nullable). It will simply be `None` for new feedback. Optional later: add a migration to drop the column if you no longer need it. |

---

## Part 6: QuickWin API (frontend → backend)

| Change | Details |
|--------|---------|
| **Frontend** | If `getQuickWin(minutes, mood)` is called with a second argument, remove the second argument so only time (and optionally no mood) is sent. |
| **Backend** | Quickwin route already builds context from request; after Part 3.1, it will use only time and energy; the request can still accept `mood` for a while and ignore it. |

---

## Order of implementation

1. **Backend first (so API no longer expects emotional_state)**  
   - Models (UserContext, SetContextRequest, SuggestFromStorageRequest)  
   - Routes (suggestions, sessions)  
   - Agents (task_suggester, quickwin_agent, orchestrator)  
   - Services/tools and repository (stop sending / storing emotional_state)

2. **Frontend second**  
   - Remove overwhelmed and low_energy from UI  
   - Remove emotional_state from API request types and from `getStoredSuggestion` and quickwin calls  
   - Simplify mood → energy_level only (3 options: enthusiastic, neutral, tired)

3. **Optional cleanup**  
   - Remove `emotional_options` from `/api/options` response  
   - Later: remove `Task.emotional_fit` and `EmotionalState` enum if you drop task-level mood fit entirely  

---

## Testing

- **UI**: Focus mode shows 3 mood options (Enthusiastic, Neutral, Tired). Suggestion and skip still work; no `emotional_state` in network request.
- **Backend**: Suggestion and quickwin endpoints accept requests without `emotional_state`; context uses only time_available and energy_level; agents and feedback no longer read or write user emotional_state; learning/feedback still work with time + energy only.
