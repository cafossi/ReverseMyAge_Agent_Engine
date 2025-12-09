"""
Weather utility for Nexus greeting personalization and on-demand requests.
Uses Open-Meteo API (free, no API key required).
"""

import httpx
from typing import Optional, Tuple

# Pre-defined coordinates for common locations
KNOWN_LOCATIONS = {
    "dallas, tx": {"lat": 32.7767, "lon": -96.7970, "tz": "America/Chicago"},
    "dallas": {"lat": 32.7767, "lon": -96.7970, "tz": "America/Chicago"},
    "frisco, tx": {"lat": 33.1507, "lon": -96.8236, "tz": "America/Chicago"},
    "frisco": {"lat": 33.1507, "lon": -96.8236, "tz": "America/Chicago"},
    "austin, tx": {"lat": 30.2672, "lon": -97.7431, "tz": "America/Chicago"},
    "austin": {"lat": 30.2672, "lon": -97.7431, "tz": "America/Chicago"},
    "houston, tx": {"lat": 29.7604, "lon": -95.3698, "tz": "America/Chicago"},
    "houston": {"lat": 29.7604, "lon": -95.3698, "tz": "America/Chicago"},
    "san antonio, tx": {"lat": 29.4241, "lon": -98.4936, "tz": "America/Chicago"},
    "san antonio": {"lat": 29.4241, "lon": -98.4936, "tz": "America/Chicago"},
    "new york, ny": {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "tz": "America/New_York"},
    "los angeles, ca": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"},
    "los angeles": {"lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles"},
    "chicago, il": {"lat": 41.8781, "lon": -87.6298, "tz": "America/Chicago"},
    "chicago": {"lat": 41.8781, "lon": -87.6298, "tz": "America/Chicago"},
    "miami, fl": {"lat": 25.7617, "lon": -80.1918, "tz": "America/New_York"},
    "miami": {"lat": 25.7617, "lon": -80.1918, "tz": "America/New_York"},
    "seattle, wa": {"lat": 47.6062, "lon": -122.3321, "tz": "America/Los_Angeles"},
    "seattle": {"lat": 47.6062, "lon": -122.3321, "tz": "America/Los_Angeles"},
    "denver, co": {"lat": 39.7392, "lon": -104.9903, "tz": "America/Denver"},
    "denver": {"lat": 39.7392, "lon": -104.9903, "tz": "America/Denver"},
    "phoenix, az": {"lat": 33.4484, "lon": -112.0740, "tz": "America/Phoenix"},
    "phoenix": {"lat": 33.4484, "lon": -112.0740, "tz": "America/Phoenix"},
    "atlanta, ga": {"lat": 33.7490, "lon": -84.3880, "tz": "America/New_York"},
    "atlanta": {"lat": 33.7490, "lon": -84.3880, "tz": "America/New_York"},
    "boston, ma": {"lat": 42.3601, "lon": -71.0589, "tz": "America/New_York"},
    "boston": {"lat": 42.3601, "lon": -71.0589, "tz": "America/New_York"},
    "las vegas, nv": {"lat": 36.1699, "lon": -115.1398, "tz": "America/Los_Angeles"},
    "las vegas": {"lat": 36.1699, "lon": -115.1398, "tz": "America/Los_Angeles"},
}

# Default location
DEFAULT_LOCATION = "Dallas, TX"


def _geocode_location(location: str) -> Optional[dict]:
    """
    Geocode a location string to coordinates using Open-Meteo Geocoding API.
    Returns dict with lat, lon, tz or None on failure.
    """
    # Check known locations first (faster)
    loc_lower = location.lower().strip()
    if loc_lower in KNOWN_LOCATIONS:
        return KNOWN_LOCATIONS[loc_lower]
    
    # Use Open-Meteo Geocoding API for unknown locations
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "tz": result.get("timezone", "UTC"),
                "name": result.get("name", location),
                "country": result.get("country", ""),
            }
        return None
    except Exception:
        return None


def _fetch_weather(lat: float, lon: float, tz: str = "UTC") -> Optional[dict]:
    """Fetch current weather from Open-Meteo API."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&temperature_unit=fahrenheit"
            f"&wind_speed_unit=mph"
            f"&timezone={tz}"
        )
        
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _weather_code_to_description(code: int) -> Tuple[str, str]:
    """Convert WMO weather code to description and emoji."""
    codes = {
        0: ("Clear sky", "☀️"),
        1: ("Mainly clear", "🌤️"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Foggy", "🌫️"),
        48: ("Depositing rime fog", "🌫️"),
        51: ("Light drizzle", "🌦️"),
        53: ("Moderate drizzle", "🌦️"),
        55: ("Dense drizzle", "🌧️"),
        61: ("Slight rain", "🌧️"),
        63: ("Moderate rain", "🌧️"),
        65: ("Heavy rain", "🌧️"),
        71: ("Slight snow", "🌨️"),
        73: ("Moderate snow", "🌨️"),
        75: ("Heavy snow", "❄️"),
        77: ("Snow grains", "❄️"),
        80: ("Slight rain showers", "🌦️"),
        81: ("Moderate rain showers", "🌧️"),
        82: ("Violent rain showers", "⛈️"),
        85: ("Slight snow showers", "🌨️"),
        86: ("Heavy snow showers", "❄️"),
        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with slight hail", "⛈️"),
        99: ("Thunderstorm with heavy hail", "⛈️"),
    }
    return codes.get(code, ("Unknown", "🌡️"))


def _format_weather_insight(temp: float, code: int, city: str) -> str:
    """Convert weather data to a brief, productivity-tied insight for greetings."""
    desc, emoji = _weather_code_to_description(code)
    
    # Productivity-tied insights based on conditions
    if code in (0, 1):  # Clear
        if temp >= 90:
            return f"{emoji} Hot {temp:.0f}°F in {city} — stay cool and let me handle the heavy lifting!"
        elif temp >= 75:
            return f"{emoji} Beautiful {temp:.0f}°F in {city} — perfect weather for productivity!"
        elif temp >= 60:
            return f"{emoji} Nice {temp:.0f}°F in {city} — great day to knock out some goals!"
        elif temp >= 45:
            return f"{emoji} Cool {temp:.0f}°F in {city} — crisp air for clear thinking!"
        else:
            return f"❄️ Cold {temp:.0f}°F in {city} — grab that coffee and let's get to work!"
    
    elif code in (2, 3, 45, 48):  # Cloudy/Fog
        return f"{emoji} {desc} and {temp:.0f}°F in {city} — good focus weather!"
    
    elif code in range(51, 68) or code in range(80, 83):  # Rain
        return f"{emoji} Rainy {temp:.0f}°F in {city} — perfect time to dive into some analysis!"
    
    elif code in range(71, 78) or code in range(85, 87):  # Snow
        return f"{emoji} Snowy {temp:.0f}°F in {city} — cozy up and let's tackle the day!"
    
    elif code in range(95, 100):  # Thunderstorms
        return f"{emoji} Stormy in {city} ({temp:.0f}°F) — let's power through some work inside!"
    
    else:
        return f"🌡️ Currently {temp:.0f}°F in {city} — let's make it a productive one!"


def get_weather_summary(location: str = DEFAULT_LOCATION) -> str:
    """
    Get a brief, productivity-tied weather insight for greetings.
    Returns empty string on failure (graceful degradation).
    
    Args:
        location: City name or "City, State" format
    
    Returns:
        Weather insight string or empty string on failure
    """
    geo = _geocode_location(location)
    if not geo:
        return ""
    
    weather = _fetch_weather(geo["lat"], geo["lon"], geo.get("tz", "UTC"))
    if not weather or "current" not in weather:
        return ""
    
    temp = weather["current"]["temperature_2m"]
    code = weather["current"]["weather_code"]
    city = geo.get("name", location.split(",")[0])
    
    return _format_weather_insight(temp, code, city)


def get_weather_detailed(location: str = DEFAULT_LOCATION) -> str:
    """
    Get detailed weather information for on-demand requests.
    
    Args:
        location: City name or "City, State" format
    
    Returns:
        Detailed weather report string
    """
    geo = _geocode_location(location)
    if not geo:
        return f"❌ Could not find location: {location}. Try a major city name like 'Austin, TX' or 'New York'."
    
    weather = _fetch_weather(geo["lat"], geo["lon"], geo.get("tz", "UTC"))
    if not weather or "current" not in weather:
        return f"❌ Could not fetch weather for {location}. Please try again."
    
    current = weather["current"]
    temp = current["temperature_2m"]
    feels_like = current["apparent_temperature"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]
    code = current["weather_code"]
    
    desc, emoji = _weather_code_to_description(code)
    city = geo.get("name", location.split(",")[0])
    country = geo.get("country", "")
    location_display = f"{city}, {country}" if country else city
    
    return f"""
{emoji} **Weather in {location_display}**

| Metric | Value |
|--------|-------|
| **Conditions** | {desc} |
| **Temperature** | {temp:.0f}°F |
| **Feels Like** | {feels_like:.0f}°F |
| **Humidity** | {humidity:.0f}% |
| **Wind** | {wind:.0f} mph |

{_format_weather_insight(temp, code, city)}
""".strip()