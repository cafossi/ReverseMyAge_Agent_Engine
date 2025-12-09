"""
Weather tool for Nexus root agent.
Allows on-demand weather lookup for any location.
"""

from google.adk.tools import FunctionTool
from ..utils.weather import get_weather_detailed, get_weather_summary


def fetch_weather(location: str) -> str:
    """
    Fetch current weather for a specified location.
    
    Use this tool when the user asks about weather in any city or location.
    Examples: "What's the weather in Austin?", "How's the weather in New York?"
    
    Args:
        location: City name (e.g., "Austin", "New York, NY", "Miami")
    
    Returns:
        Formatted weather report with conditions, temperature, humidity, and wind.
    """
    return get_weather_detailed(location)


# Create ADK-compatible tool
weather_tool = FunctionTool(func=fetch_weather)