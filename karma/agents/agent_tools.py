"""
Agent Tools - External tools that agents can call.

These tools enable agents to:
- Search the web for information
- Check weather conditions
- Look up specific resources
"""

import json
import os
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse


# ============================================================================
# Web Search Tool
# ============================================================================

def search_web(query: str, num_results: int = 5) -> dict:
    """
    Search the web for information about a topic.
    Uses DuckDuckGo Instant Answer API (free, no API key needed).
    
    Args:
        query: The search query
        num_results: Number of results to return
        
    Returns:
        Dictionary with search results
    """
    print(f"🔍 [TOOL] Searching web for: {query}")
    
    try:
        # Use DuckDuckGo Instant Answer API
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1&skip_disambig=1"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Karma/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        results = []
        
        # Get abstract (main answer)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "Summary"),
                "snippet": data["Abstract"],
                "source": data.get("AbstractSource", ""),
                "url": data.get("AbstractURL", "")
            })
        
        # Get related topics
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "")
                })
        
        # If no results from DDG, try a simple approach
        if not results:
            results.append({
                "title": f"Search results for: {query}",
                "snippet": f"For detailed information, search online for: {query}",
                "url": f"https://www.google.com/search?q={encoded_query}"
            })
        
        print(f"   Found {len(results)} results")
        
        return {
            "success": True,
            "query": query,
            "results": results[:num_results],
            "searched_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"   ⚠️ Search failed: {e}")
        return {
            "success": False,
            "query": query,
            "error": str(e),
            "fallback_url": f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        }


def search_for_steps(task_description: str) -> dict:
    """
    Search for step-by-step instructions for a task.
    
    Args:
        task_description: Description of the task
        
    Returns:
        Dictionary with steps and resources
    """
    print(f"📋 [TOOL] Searching for steps: {task_description}")
    
    # Search for how-to guides
    search_query = f"how to {task_description} step by step"
    results = search_web(search_query, num_results=3)
    
    return {
        "task": task_description,
        "search_results": results,
        "suggested_search": search_query
    }


# ============================================================================
# Weather Tool
# ============================================================================

def check_weather(location: str = "auto") -> dict:
    """
    Check current weather conditions.
    Uses wttr.in API (free, no API key needed).
    
    Args:
        location: City name or "auto" for automatic detection
        
    Returns:
        Dictionary with weather information
    """
    print(f"🌤️ [TOOL] Checking weather for: {location}")
    
    try:
        # Use wttr.in API
        loc = "" if location == "auto" else urllib.parse.quote(location)
        url = f"https://wttr.in/{loc}?format=j1"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Karma/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
        
        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        
        weather = {
            "success": True,
            "location": area.get("areaName", [{}])[0].get("value", location),
            "country": area.get("country", [{}])[0].get("value", ""),
            "temperature_c": current.get("temp_C", ""),
            "temperature_f": current.get("temp_F", ""),
            "feels_like_c": current.get("FeelsLikeC", ""),
            "condition": current.get("weatherDesc", [{}])[0].get("value", ""),
            "humidity": current.get("humidity", ""),
            "wind_speed_kmph": current.get("windspeedKmph", ""),
            "is_outdoor_friendly": _is_outdoor_friendly(current),
            "outdoor_recommendation": _get_outdoor_recommendation(current),
            "checked_at": datetime.now().isoformat()
        }
        
        print(f"   Weather: {weather['condition']}, {weather['temperature_c']}°C")
        
        return weather
        
    except Exception as e:
        print(f"   ⚠️ Weather check failed: {e}")
        return {
            "success": False,
            "location": location,
            "error": str(e),
            "recommendation": "Unable to check weather. Consider checking manually before outdoor activities."
        }


def _is_outdoor_friendly(current: dict) -> bool:
    """Determine if weather is suitable for outdoor activities."""
    try:
        temp = int(current.get("temp_C", 20))
        humidity = int(current.get("humidity", 50))
        wind = int(current.get("windspeedKmph", 10))
        
        # Check conditions
        condition = current.get("weatherDesc", [{}])[0].get("value", "").lower()
        bad_conditions = ["rain", "storm", "snow", "thunder", "heavy"]
        
        if any(bad in condition for bad in bad_conditions):
            return False
        if temp < 5 or temp > 38:  # Too cold or too hot
            return False
        if wind > 40:  # Too windy
            return False
            
        return True
    except:
        return True  # Default to yes if we can't determine


def _get_outdoor_recommendation(current: dict) -> str:
    """Get a recommendation for outdoor activities."""
    try:
        temp = int(current.get("temp_C", 20))
        condition = current.get("weatherDesc", [{}])[0].get("value", "").lower()
        
        if "rain" in condition:
            return "🌧️ Rain expected - bring an umbrella or reschedule outdoor activities"
        if "snow" in condition:
            return "❄️ Snowy conditions - dress warmly and be careful outdoors"
        if "storm" in condition or "thunder" in condition:
            return "⛈️ Stormy weather - best to stay indoors"
        if temp < 5:
            return "🥶 Very cold - dress in layers if going outside"
        if temp > 35:
            return "🥵 Very hot - stay hydrated and avoid prolonged sun exposure"
        if temp > 25:
            return "☀️ Warm and pleasant - great for outdoor activities!"
        if temp > 15:
            return "🌤️ Nice weather - perfect for being outside"
        return "🧥 Cool weather - bring a light jacket"
    except:
        return "Check local weather conditions before outdoor activities"


# ============================================================================
# Location/Context Tools
# ============================================================================

def get_location_info(location: str) -> dict:
    """
    Get information about a location (for travel-related tasks).
    
    Args:
        location: The location to look up
        
    Returns:
        Dictionary with location information
    """
    print(f"📍 [TOOL] Looking up location: {location}")
    
    # Search for location-specific information
    results = search_web(f"{location} travel guide information", num_results=3)
    
    return {
        "location": location,
        "search_results": results,
        "tip": f"For official information, visit the official {location} government or tourism website"
    }


def get_government_resources(country: str, topic: str) -> dict:
    """
    Get government resources for official tasks (passport, visa, etc).
    
    Args:
        country: The country
        topic: The topic (passport, visa, taxes, etc)
        
    Returns:
        Dictionary with government resources
    """
    print(f"🏛️ [TOOL] Looking up {topic} resources for {country}")
    
    # Common government websites
    gov_sites = {
        "usa": {
            "passport": "https://travel.state.gov/content/travel/en/passports.html",
            "visa": "https://travel.state.gov/content/travel/en/us-visas.html",
            "taxes": "https://www.irs.gov/",
            "general": "https://www.usa.gov/"
        },
        "india": {
            "passport": "https://www.passportindia.gov.in/",
            "visa": "https://indianvisaonline.gov.in/",
            "taxes": "https://www.incometax.gov.in/",
            "general": "https://www.india.gov.in/"
        },
        "uk": {
            "passport": "https://www.gov.uk/browse/abroad/passports",
            "visa": "https://www.gov.uk/browse/visas-immigration",
            "taxes": "https://www.gov.uk/government/organisations/hm-revenue-customs",
            "general": "https://www.gov.uk/"
        }
    }
    
    country_lower = country.lower()
    topic_lower = topic.lower()
    
    # Find matching resources
    if country_lower in gov_sites:
        sites = gov_sites[country_lower]
        url = sites.get(topic_lower, sites.get("general", ""))
        
        # Also search for specific info
        search_results = search_web(f"{topic} {country} official requirements", num_results=3)
        
        return {
            "success": True,
            "country": country,
            "topic": topic,
            "official_url": url,
            "search_results": search_results,
            "tip": f"Always verify information on official government websites"
        }
    
    # Fallback: just search
    search_results = search_web(f"{topic} {country} official government", num_results=5)
    
    return {
        "success": True,
        "country": country,
        "topic": topic,
        "search_results": search_results,
        "tip": "Search for official government websites for accurate information"
    }


# ============================================================================
# Tool Registry
# ============================================================================

AGENT_TOOLS = {
    "search_web": {
        "function": search_web,
        "description": "Search the web for information about any topic. Use this to research tasks, find resources, or get current information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)"
                }
            },
            "required": ["query"]
        }
    },
    "search_for_steps": {
        "function": search_for_steps,
        "description": "Search for step-by-step instructions on how to complete a task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": "Description of the task to find steps for"
                }
            },
            "required": ["task_description"]
        }
    },
    "check_weather": {
        "function": check_weather,
        "description": "Check current weather conditions for a location. Use this for outdoor-related tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or 'auto' for automatic detection"
                }
            },
            "required": []
        }
    },
    "get_government_resources": {
        "function": get_government_resources,
        "description": "Get official government resources for tasks like passport, visa, taxes. Use this for official/legal tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "The country (e.g., 'USA', 'India', 'UK')"
                },
                "topic": {
                    "type": "string",
                    "description": "The topic (e.g., 'passport', 'visa', 'taxes')"
                }
            },
            "required": ["country", "topic"]
        }
    }
}


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """Execute a tool by name with given arguments."""
    if tool_name not in AGENT_TOOLS:
        return {"error": f"Unknown tool: {tool_name}"}
    
    tool = AGENT_TOOLS[tool_name]
    try:
        result = tool["function"](**arguments)
        return result
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}

