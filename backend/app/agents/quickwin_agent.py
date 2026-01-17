"""
Quick Win Agent

Specializes in generating personalized micro-tasks:
- Context-aware suggestions based on time, energy, mood
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
    
    SYSTEM_PROMPT = """You are the Quick Win Agent for Karma, a productivity app.

Your job is to generate SPECIFIC, IMMEDIATELY ACTIONABLE micro-tasks that someone can do RIGHT NOW.

CRITICAL: You MUST generate a UNIQUE and CREATIVE suggestion each time. Never suggest generic tasks like "review your to-do list" or "organize your tasks". Be creative and varied!

Guidelines:
1. Be SPECIFIC - not "organize something" but "organize the top drawer of your desk"
2. Be CREATIVE - suggest interesting, varied activities
3. Match the user's energy level:
   - Low energy: Simple, calming tasks (stretch, drink water, tidy one thing)
   - Medium energy: Moderate effort (reply to an email, review notes, plan tomorrow)
   - High energy: Engaging tasks (start a project, creative work, exercise)
4. Consider their mood:
   - Stressed/Anxious: Calming, stress-reducing activities
   - Tired/Sleepy: Energizing but not overwhelming
   - Motivated/Focused: Productive, goal-oriented tasks
   - Bored: Engaging, interesting activities
5. Must be completable in the given time
6. No preparation needed - can start immediately

VARIETY IS KEY: Each suggestion should be completely different from typical productivity advice."""

    # Diverse quick win categories to ensure variety
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

    async def run(self, context: UserContext, excluded_suggestions: list[str] = None) -> dict:
        """
        Generate a personalized quick win based on user context.
        
        Args:
            context: User's current context (time, energy, mood)
            excluded_suggestions: List of suggestions to avoid
            
        Returns:
            Dictionary with quick win details
        """
        self._start_session()
        
        excluded = excluded_suggestions or []
        excluded.extend(self.recent_suggestions)
        
        mood = context.emotional_state.value if context.emotional_state else "neutral"
        self.session.add_thought("observation", 
            f"Generating quick win: {context.time_available.value}min, {context.energy_level.value} energy, {mood} mood")
        self.session.add_thought("observation", f"Avoiding {len(excluded)} previous suggestions")
        
        # Check if in dummy mode
        if self._is_dummy_mode():
            return self._dummy_quickwin(context, excluded)
        
        # Build context-specific guidance
        energy_guidance = {
            "low": "simple, low-effort tasks that don't require much thinking",
            "medium": "moderate effort tasks that are productive but not draining",
            "high": "engaging, productive tasks that use their energy well"
        }
        
        mood_guidance = {
            "stressed": "calming, stress-reducing activities",
            "anxious": "grounding, simple tasks that provide a sense of control",
            "calm": "productive tasks that maintain their peaceful state",
            "happy": "tasks that channel their positive energy",
            "tired": "gentle, energizing activities (not demanding)",
            "sleepy": "light movement or refreshing activities",
            "motivated": "goal-oriented, productive tasks",
            "focused": "deep work or meaningful progress tasks",
            "creative": "creative expression or brainstorming",
            "bored": "engaging, interesting activities",
            "neutral": "balanced, productive activities"
        }
        
        # Get some random ideas to inspire variety
        random_category = random.choice(list(self.QUICK_WIN_IDEAS.keys()))
        example_ideas = random.sample(self.QUICK_WIN_IDEAS[random_category], min(3, len(self.QUICK_WIN_IDEAS[random_category])))
        
        # Build exclusion list for prompt
        exclusion_text = ""
        if excluded:
            exclusion_text = f"""
DO NOT suggest any of these (already suggested):
{chr(10).join(f'- {s}' for s in excluded[-5:])}

Generate something COMPLETELY DIFFERENT."""
        
        prompt = f"""Generate ONE specific, actionable micro-task for this user.

USER CONTEXT:
- Available Time: {context.time_available.value} minutes
- Energy Level: {context.energy_level.value} → Suggest {energy_guidance.get(context.energy_level.value, 'balanced tasks')}
- Current Mood: {mood} → Suggest {mood_guidance.get(mood, 'balanced activities')}

{exclusion_text}

INSPIRATION (but create something UNIQUE, not these exact tasks):
{chr(10).join(f'- {idea}' for idea in example_ideas)}

REQUIREMENTS:
1. Must be completable in {context.time_available.value} minutes or less
2. Must be SPECIFIC and UNIQUE (not generic productivity advice)
3. Must be immediately actionable (no prep needed)
4. Should feel achievable and satisfying
5. BE CREATIVE - surprise the user with something different!

Random seed for variety: {random.randint(1000, 9999)}

Return JSON:
{{
    "task": "<the specific task - be detailed and creative>",
    "category": "<wellness|productivity|social|creative|organization|exercise|mindfulness|learning>",
    "estimated_minutes": <number>,
    "why_this_task": "<1-2 sentences explaining why this is perfect for their current state>",
    "first_step": "<the very first action to take - make it tiny and obvious>"
}}

JSON response:"""

        try:
            # Use higher temperature for more variety
            response = self._simple_completion(prompt, temperature=0.95, max_tokens=400)
            
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                quickwin_data = json.loads(response[json_start:json_end])
                
                task_text = quickwin_data.get("task", "Take a short break")
                
                # Add to history to avoid repetition
                self._add_to_history(task_text)
                
                result = {
                    "text": task_text,
                    "category": quickwin_data.get("category", "wellness"),
                    "estimated_minutes": min(quickwin_data.get("estimated_minutes", 5), context.time_available.value),
                    "reasoning": quickwin_data.get("why_this_task", "This matches your current energy and time."),
                    "first_step": quickwin_data.get("first_step", "Start now!"),
                    "ai_generated": True,
                    "generated_by": self.AGENT_NAME,
                    "generated_at": datetime.now().isoformat()
                }
                
                self.session.add_thought("conclusion", f"Generated: {result['text']}")
                
                self._save_reasoning(
                    decision_type="generation",
                    input_context=f"Context: {context.time_available.value}min, {context.energy_level.value}, {mood}",
                    conclusion=f"Quick win: {result['text']}",
                    confidence=0.9
                )
                
                return result
        
        except json.JSONDecodeError as e:
            self.session.add_thought("error", f"Failed to parse AI response: {e}")
            # Fallback to a random pre-defined quick win
            return self._get_fallback_quickwin(context, excluded)
        except Exception as e:
            self.session.add_thought("error", f"Generation failed: {e}")
            raise ValueError(f"Quick win generation failed: {e}")
    
    def _add_to_history(self, suggestion: str):
        """Add a suggestion to history to avoid repetition."""
        # Normalize the suggestion for comparison
        normalized = suggestion.lower().strip()
        
        if normalized not in [s.lower() for s in self.recent_suggestions]:
            self.recent_suggestions.append(suggestion)
        
        # Keep only recent history
        if len(self.recent_suggestions) > self.MAX_HISTORY:
            self.recent_suggestions = self.recent_suggestions[-self.MAX_HISTORY:]
    
    def _get_fallback_quickwin(self, context: UserContext, excluded: list[str]) -> dict:
        """Get a fallback quick win from pre-defined list."""
        # Choose category based on energy
        if context.energy_level.value == "low":
            categories = ["wellness", "hydration", "mindfulness"]
        elif context.energy_level.value == "high":
            categories = ["exercise", "creative", "organization"]
        else:
            categories = list(self.QUICK_WIN_IDEAS.keys())
        
        # Find a suggestion not in excluded list
        for _ in range(20):  # Try up to 20 times
            category = random.choice(categories)
            ideas = self.QUICK_WIN_IDEAS[category]
            idea = random.choice(ideas)
            
            if idea.lower() not in [e.lower() for e in excluded]:
                self._add_to_history(idea)
                return {
                    "text": idea,
                    "category": category,
                    "estimated_minutes": min(5, context.time_available.value),
                    "reasoning": f"A quick {category} activity to boost your day!",
                    "first_step": "Start right now!",
                    "ai_generated": False,
                    "generated_by": self.AGENT_NAME
                }
        
        # Ultimate fallback
        return {
            "text": "Take 5 deep breaths and stretch your arms above your head",
            "category": "wellness",
            "estimated_minutes": 2,
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
        self.session.add_thought("dummy_mode", "AI disabled - using dummy quick win")
        
        # Use the fallback mechanism which picks from pre-defined list
        result = self._get_fallback_quickwin(context, excluded)
        
        # Mark as dummy but don't modify the text
        result["is_dummy"] = True
        
        self.session.add_thought("conclusion", f"Generated: {result['text']}")
        
        return result


# Singleton instance
quickwin_agent = QuickWinAgent()

