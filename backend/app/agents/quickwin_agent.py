"""
Quick Win Agent

Specializes in generating personalized micro-tasks:
- Context-aware suggestions based on time and energy
- Immediately actionable (no preparation needed)
- Provides first step to get started
- Tracks history to avoid repetition
"""

import json
import random
from datetime import datetime

from app.models import UserContext
from .base_agent import BaseAgent


class QuickWinAgent(BaseAgent):
    """Agent that generates personalized quick win micro-tasks."""
    
    AGENT_NAME = "QuickWin"
    
    # Track recently suggested quick wins to avoid repetition
    recent_suggestions: list[str] = []
    MAX_HISTORY = 10
    
    SYSTEM_PROMPT = """IDENTITY & CORE RULES (Initialization)
You are the Quick Win Agent for Karma, a productivity app. Your job is to generate ONE specific, immediately actionable micro-task for the user.

CRITICAL CONSTRAINTS:
1. The generated task text must be UNDER 20 WORDS.
2. Time-tightness: The estimated_minutes you return MUST satisfy:
   estimated_minutes <= available_minutes AND (available_minutes - estimated_minutes) <= 2.
   Example: available=5 → estimated_minutes must be 3, 4, or 5.
   Example: available=10 → estimated_minutes must be 8, 9, or 10.
3. Zero Decision: The user should not have to choose anything to start.

STYLE GUIDELINES:
- Direct & Disciplined: Use a direct tone. No sentimental framing or lifestyle-fluff.
- Immediately Executable: Tasks must be self-contained and finite. No prior artifacts needed.
- No Dependencies: Do not generate tasks that require searching, brainstorming, or abstract ideation.
- Bounded Outputs: Scope by numbers (e.g., "3 items," "5 bullets") rather than ambiguity.
- Match Activation: Match the task strictly to the activation level of the energy.

FEW-SHOT EXAMPLES:
Context: Energy: low | Available: 5 min
BAD: "Create a themed playlist called 'Cozy Reading' with 5-7 songs." (Decision-heavy, requires searching).
GOOD: "Read one pre-saved article without switching tabs." (Zero-decision, restorative, est=4min, gap=1).

Context: Energy: medium | Available: 10 min
BAD: "Spend 10 minutes brainstorming video ideas focusing on fun concepts." (Abstract, brainstorming-heavy).
GOOD: "Write 3 bullet-point notes from yesterday's meeting." (Self-contained, bounded, est=9min, gap=1).

Context: Energy: high | Available: 15 min
BAD: "Select an item and write a playful letter to a friend describing its origins." (Artificial, sentimental).
GOOD: "Outline one sharp insight to share publicly; structure into 3-5 bullets." (Action-oriented, est=14min, gap=1)."""

    # Diverse quick win ideas for variety (fallback and inspiration)
    QUICK_WIN_IDEAS = {
        "wellness": [
            "Do 10 shoulder rolls, 5 each direction",
            "Take 5 deep breaths using the 4-7-8 technique",
            "Stand up and touch your toes 5 times",
            "Do a 1-minute wall sit",
            "Massage your temples for 30 seconds",
            "Do 10 calf raises while standing",
            "Stretch your wrists and fingers for a minute",
            "Roll your neck slowly in circles 5 times each way"
        ],
        "hydration": [
            "Drink a full glass of water right now",
            "Make yourself a cup of herbal tea",
            "Refill your water bottle and drink half of it",
            "Have a glass of water with lemon"
        ],
        "social": [
            "Send a 'thinking of you' text to a friend",
            "Reply to one message you've been putting off",
            "Send a funny meme to someone who needs a laugh",
            "Write a quick thank you message to someone",
            "Comment something nice on a friend's social media post"
        ],
        "organization": [
            "Clear 5 items from your desk",
            "Delete 10 old emails from your inbox",
            "Organize your browser bookmarks for 3 minutes",
            "Put away 3 things that are out of place",
            "Sort through one drawer quickly",
            "Unsubscribe from 3 email newsletters you don't read"
        ],
        "mindfulness": [
            "Look out the window and notice 5 different colors",
            "Listen and identify 3 different sounds around you",
            "Close your eyes and focus on your breathing for 60 seconds",
            "Write down 3 things you're grateful for today",
            "Take a photo of something beautiful near you"
        ],
        "creative": [
            "Doodle something random for 2 minutes",
            "Write a haiku about your current mood",
            "Think of 3 creative uses for a paperclip",
            "Sketch the view from your window",
            "Write down a random story idea in one sentence"
        ],
        "learning": [
            "Read one interesting article for 5 minutes",
            "Learn one new word and use it in a sentence",
            "Watch a 3-minute educational video",
            "Look up one fact about a topic you're curious about"
        ],
        "exercise": [
            "Do 15 jumping jacks",
            "Hold a plank for 30 seconds",
            "Do 10 squats right where you are",
            "Walk around your space for 2 minutes",
            "Do 10 push-ups (or wall push-ups)",
            "March in place for 1 minute"
        ]
    }

    async def run(self, context: UserContext, excluded_suggestions: list[str] = None, user_id: str = None) -> dict:
        """
        Generate a personalized quick win based on user context.
        """
        self._start_session()
        
        excluded = excluded_suggestions or []
        excluded.extend(self.recent_suggestions)
        available_minutes = context.time_available.value
        min_minutes = max(1, available_minutes - 2)
        
        if self.session:
            self.session.add_thought("observation", 
                f"Generating quick win: {available_minutes}min, {context.energy_level.value} energy, time-tight window={min_minutes}-{available_minutes}min")
            self.session.add_thought("observation", f"Avoiding {len(excluded)} previous suggestions")
        
        # Get user preferences and past behavior if user_id provided
        user_preferences = ""
        past_behavior = ""
        if user_id:
            try:
                from app.services import db_service
                
                insights = await db_service.get_learning_insights(user_id)
                if insights:
                    acceptance_rate = insights.get("acceptance_rate", 0)
                    total_feedback = insights.get("total_feedback", 0)
                    if total_feedback > 0:
                        past_behavior = f"""
PAST BEHAVIOR ANALYSIS:
- Acceptance rate: {acceptance_rate:.0%}
- Preferred categories: {insights.get('preferred_categories', 'No clear pattern yet')}
"""
                
                all_tasks = await db_service.get_all_tasks(user_id)
                if all_tasks:
                    categories = {}
                    for task in all_tasks:
                        cat = task.get("category", "other")
                        categories[cat] = categories.get(cat, 0) + 1
                    
                    if categories:
                        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
                        user_preferences = f"""
USER PREFERENCES (inferred from task history):
- Top categories: {', '.join([f'{cat} ({count})' for cat, count in top_categories])}
"""
            except Exception as e:
                if self.session:
                    self.session.add_thought("observation", f"Could not load user preferences: {e}")
        
        if self._is_dummy_mode():
            return self._dummy_quickwin(context, excluded)
        
        energy_guidance = {
            "low": "simple, low-effort tasks that don't require much thinking",
            "medium": "moderate effort tasks that are productive but not draining",
            "high": "engaging, productive tasks that use their energy well"
        }
        
        random_category = random.choice(list(self.QUICK_WIN_IDEAS.keys()))
        example_ideas = random.sample(self.QUICK_WIN_IDEAS[random_category], min(3, len(self.QUICK_WIN_IDEAS[random_category])))
        
        exclusion_text = ""
        if excluded:
            exclusion_text = f"""
DO NOT suggest any of these (already suggested):
{chr(10).join(f'- {s}' for s in excluded[-5:])}

Generate something COMPLETELY DIFFERENT."""
        
        emotional_context = f", Mood: {context.emotional_state.value}" if hasattr(context, 'emotional_state') and context.emotional_state else ""
        
        prompt = f"""Generate ONE specific, actionable micro-task for this user.

USER CONTEXT:
- Available Time: {available_minutes} minutes
- Energy Level: {context.energy_level.value}{emotional_context}
- Goal: Suggest {energy_guidance.get(context.energy_level.value, 'balanced tasks')}

TIME-TIGHTNESS RULE (mandatory):
- estimated_minutes MUST be between {min_minutes} and {available_minutes} (inclusive).
- The gap (available - estimated) must be <= 2.

{past_behavior}

{user_preferences}

{exclusion_text}

INSPIRATION (create something UNIQUE and under 20 words):
{chr(10).join(f'- {idea}' for idea in example_ideas)}

Random seed for variety: {random.randint(1000, 9999)}

Return JSON:
{{
    "task": "<the specific task - under 20 words>",
    "category": "<wellness|productivity|social|creative|organization|exercise|mindfulness|learning>",
    "estimated_minutes": <number between {min_minutes} and {available_minutes}>,
    "why_this_task": "<1 sentence>",
    "first_step": "<tiny, obvious first action>"
}}

JSON response:"""

        try:
            response = await self._simple_completion(
                prompt, 
                temperature=0.7, 
                max_tokens=400,
                user_id=user_id,
                operation_type="quickwin"
            )
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                quickwin_data = json.loads(response[json_start:json_end])
                
                task_text = quickwin_data.get("task", "Take a short break")
                raw_est = quickwin_data.get("estimated_minutes", available_minutes)
                clamped_est = max(min_minutes, min(raw_est, available_minutes))
                
                self._add_to_history(task_text)
                
                result = {
                    "text": task_text,
                    "category": quickwin_data.get("category", "wellness"),
                    "estimated_minutes": clamped_est,
                    "reasoning": quickwin_data.get("why_this_task", "This matches your current energy and time."),
                    "first_step": quickwin_data.get("first_step", "Start now!"),
                    "ai_generated": True,
                    "generated_by": self.AGENT_NAME,
                    "generated_at": datetime.now().isoformat()
                }
                
                if self.session:
                    self.session.add_thought("conclusion", f"Generated: {result['text']} (est={clamped_est}min, gap={available_minutes - clamped_est})")
                
                self._save_reasoning(
                    decision_type="generation",
                    input_context=f"Context: {available_minutes}min, {context.energy_level.value}",
                    conclusion=f"Quick win: {result['text']}",
                    confidence=0.9
                )
                
                return result
        
        except json.JSONDecodeError as e:
            if self.session:
                self.session.add_thought("error", f"Failed to parse AI response: {e}")
            return self._get_fallback_quickwin(context, excluded)
        except Exception as e:
            if self.session:
                self.session.add_thought("error", f"Generation failed: {e}")
            raise ValueError(f"Quick win generation failed: {e}")
    
    def _add_to_history(self, suggestion: str):
        """Add a suggestion to history to avoid repetition."""
        normalized = suggestion.lower().strip()
        
        if normalized not in [s.lower() for s in self.recent_suggestions]:
            self.recent_suggestions.append(suggestion)
        
        if len(self.recent_suggestions) > self.MAX_HISTORY:
            self.recent_suggestions = self.recent_suggestions[-self.MAX_HISTORY:]
    
    def _get_fallback_quickwin(self, context: UserContext, excluded: list[str]) -> dict:
        """Get a fallback quick win from pre-defined list."""
        available_minutes = context.time_available.value
        min_minutes = max(1, available_minutes - 2)
        
        if context.energy_level.value == "low":
            categories = ["wellness", "hydration", "mindfulness"]
        elif context.energy_level.value == "high":
            categories = ["exercise", "creative", "organization"]
        else:
            categories = list(self.QUICK_WIN_IDEAS.keys())
        
        for _ in range(20):
            category = random.choice(categories)
            ideas = self.QUICK_WIN_IDEAS[category]
            idea = random.choice(ideas)
            
            if idea.lower() not in [e.lower() for e in excluded]:
                self._add_to_history(idea)
                return {
                    "text": idea,
                    "category": category,
                    "estimated_minutes": min(available_minutes, max(min_minutes, 3)),
                    "reasoning": f"A quick {category} activity that fits your time window.",
                    "first_step": "Start right now!",
                    "ai_generated": False,
                    "generated_by": self.AGENT_NAME
                }
        
        return {
            "text": "Take 5 deep breaths and stretch your arms above your head",
            "category": "wellness",
            "estimated_minutes": min(available_minutes, max(min_minutes, 2)),
            "reasoning": "A simple reset for body and mind.",
            "first_step": "Stand up or sit up straight.",
            "ai_generated": False,
            "generated_by": self.AGENT_NAME
        }
    
    def clear_history(self):
        """Clear the suggestion history."""
        self.recent_suggestions = []
    
    def _dummy_quickwin(self, context: UserContext, excluded: list[str]) -> dict:
        """Generate dummy quick win when AI is not enabled."""
        if self.session:
            self.session.add_thought("dummy_mode", "AI disabled - using dummy quick win")
        
        result = self._get_fallback_quickwin(context, excluded)
        result["is_dummy"] = True
        
        if self.session:
            self.session.add_thought("conclusion", f"Generated: {result['text']}")
        
        return result


# Singleton instance
quickwin_agent = QuickWinAgent()
