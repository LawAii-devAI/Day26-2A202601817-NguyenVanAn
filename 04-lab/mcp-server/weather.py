from typing import Any
import asyncio
import httpx
import os
import sys
from datetime import datetime, timedelta

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
port = int(os.getenv("PORT", 8085))
mcp = FastMCP("weather", host="0.0.0.0", port=port)

# Constants
WEATHERAPI_BASE = "https://api.weatherapi.com/v1"
USER_AGENT = "weather-app/1.0"

# Get API key from environment variable
API_KEY = os.getenv("WEATHERAPI_KEY")

# Simulated / Mock data database for fallback
MOCK_CITIES = {
    "hanoi": {
        "name": "Hanoi", "region": "Ha Noi", "country": "Vietnam",
        "temp_c": 29.0, "temp_f": 84.2, "feelslike_c": 33.5, "feelslike_f": 92.3,
        "condition": "Patchy light rain with thunderstorm", "humidity": 82,
        "wind_kph": 12.5, "wind_mph": 7.8, "wind_dir": "SE",
        "pressure_mb": 1008.0, "uv": 6.0, "vis_km": 9.0,
    },
    "ho chi minh": {
        "name": "Ho Chi Minh City", "region": "Ho Chi Minh", "country": "Vietnam",
        "temp_c": 33.0, "temp_f": 91.4, "feelslike_c": 38.0, "feelslike_f": 100.4,
        "condition": "Scattered showers", "humidity": 75,
        "wind_kph": 15.0, "wind_mph": 9.3, "wind_dir": "SW",
        "pressure_mb": 1010.0, "uv": 8.0, "vis_km": 10.0,
    },
    "danang": {
        "name": "Danang", "region": "Da Nang", "country": "Vietnam",
        "temp_c": 30.5, "temp_f": 86.9, "feelslike_c": 35.0, "feelslike_f": 95.0,
        "condition": "Partly cloudy", "humidity": 78,
        "wind_kph": 10.0, "wind_mph": 6.2, "wind_dir": "E",
        "pressure_mb": 1011.0, "uv": 7.0, "vis_km": 10.0,
    },
    "haiphong": {
        "name": "Haiphong", "region": "Hai Phong", "country": "Vietnam",
        "temp_c": 29.5, "temp_f": 85.1, "feelslike_c": 34.0, "feelslike_f": 93.2,
        "condition": "Moderate rain", "humidity": 84,
        "wind_kph": 14.0, "wind_mph": 8.7, "wind_dir": "SE",
        "pressure_mb": 1009.0, "uv": 5.0, "vis_km": 8.0,
    },
    "brisbane": {
        "name": "Brisbane", "region": "Queensland", "country": "Australia",
        "temp_c": 24.0, "temp_f": 75.2, "feelslike_c": 24.5, "feelslike_f": 76.1,
        "condition": "Sunny and clear", "humidity": 62,
        "wind_kph": 18.0, "wind_mph": 11.2, "wind_dir": "E",
        "pressure_mb": 1018.0, "uv": 6.0, "vis_km": 10.0,
    },
    "sydney": {
        "name": "Sydney", "region": "New South Wales", "country": "Australia",
        "temp_c": 21.5, "temp_f": 70.7, "feelslike_c": 21.0, "feelslike_f": 69.8,
        "condition": "Partly cloudy", "humidity": 65,
        "wind_kph": 20.0, "wind_mph": 12.4, "wind_dir": "S",
        "pressure_mb": 1020.0, "uv": 5.0, "vis_km": 10.0,
    },
    "melbourne": {
        "name": "Melbourne", "region": "Victoria", "country": "Australia",
        "temp_c": 18.0, "temp_f": 64.4, "feelslike_c": 17.5, "feelslike_f": 63.5,
        "condition": "Overcast with light breeze", "humidity": 68,
        "wind_kph": 22.0, "wind_mph": 13.7, "wind_dir": "W",
        "pressure_mb": 1016.0, "uv": 4.0, "vis_km": 10.0,
    },
    "tokyo": {
        "name": "Tokyo", "region": "Tokyo", "country": "Japan",
        "temp_c": 19.0, "temp_f": 66.2, "feelslike_c": 19.0, "feelslike_f": 66.2,
        "condition": "Clear", "humidity": 55,
        "wind_kph": 10.0, "wind_mph": 6.2, "wind_dir": "NE",
        "pressure_mb": 1015.0, "uv": 5.0, "vis_km": 10.0,
    },
}

def get_mock_city_data(city: str) -> dict[str, Any]:
    """Return realistic mock data for any city."""
    normalized = city.strip().lower()
    for key, data in MOCK_CITIES.items():
        if key in normalized or normalized in key:
            return data
    
    # Generic fallback for unlisted cities
    title_name = city.strip().title()
    return {
        "name": title_name, "region": title_name, "country": "Global",
        "temp_c": 25.0, "temp_f": 77.0, "feelslike_c": 26.0, "feelslike_f": 78.8,
        "condition": "Mild and partly cloudy", "humidity": 65,
        "wind_kph": 12.0, "wind_mph": 7.5, "wind_dir": "NE",
        "pressure_mb": 1013.0, "uv": 5.0, "vis_km": 10.0,
    }

async def make_weather_request(endpoint: str, params: dict[str, str]) -> dict[str, Any] | None:
    """Make a request to the WeatherAPI with proper error handling."""
    if not API_KEY:
        return None
        
    headers = {
        "User-Agent": USER_AGENT,
    }
    params["key"] = API_KEY
    url = f"{WEATHERAPI_BASE}/{endpoint}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"WeatherAPI request failed: {e}")
            return None

@mcp.tool()
async def get_current_weather(city: str) -> str:
    """Get current weather conditions for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney")
    """
    params = {
        "q": city,
        "aqi": "no"
    }
    
    data = await make_weather_request("current.json", params)

    if not data:
        # Fallback to simulated mock data
        mock = get_mock_city_data(city)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""Current Weather for {mock['name']}, {mock['region']}, {mock['country']}:

Temperature: {mock['temp_c']}°C ({mock['temp_f']}°F)
Feels like: {mock['feelslike_c']}°C ({mock['feelslike_f']}°F)
Condition: {mock['condition']}
Humidity: {mock['humidity']}%
Wind: {mock['wind_kph']} km/h ({mock['wind_mph']} mph) {mock['wind_dir']}
Pressure: {mock['pressure_mb']} mb
UV Index: {mock['uv']}
Visibility: {mock['vis_km']} km

Last updated: {now_str}
(Note: Using simulated weather telemetry)"""

    current = data["current"]
    location = data["location"]
    
    return f"""Current Weather for {location['name']}, {location['region']}, {location['country']}:

Temperature: {current['temp_c']}°C ({current['temp_f']}°F)
Feels like: {current['feelslike_c']}°C ({current['feelslike_f']}°F)
Condition: {current['condition']['text']}
Humidity: {current['humidity']}%
Wind: {current['wind_kph']} km/h ({current['wind_mph']} mph) {current['wind_dir']}
Pressure: {current['pressure_mb']} mb
UV Index: {current['uv']}
Visibility: {current['vis_km']} km

Last updated: {current['last_updated']}"""

@mcp.tool()
async def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast for a city.

    Args:
        city: City name (e.g., "Hanoi", "Haiphong", "Danang", "Brisbane", "Sydney", "Melbourne")
        days: Number of days to forecast (1-3 for free tier, max 10 for paid)
    """
    days = min(max(days, 1), 3)
    
    params = {
        "q": city,
        "days": str(days),
        "aqi": "no",
        "alerts": "no"
    }
    
    data = await make_weather_request("forecast.json", params)

    if not data:
        # Fallback to simulated forecast data
        mock = get_mock_city_data(city)
        forecasts = [f"Weather Forecast for {mock['name']}, {mock['region']}, {mock['country']}:"]
        
        today = datetime.now()
        conditions = [mock['condition'], "Partly cloudy with sunny intervals", "Scattered rain showers"]
        for i in range(days):
            day_date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            high_c = round(mock['temp_c'] + 1.5 - (i * 0.5), 1)
            low_c = round(mock['temp_c'] - 4.0 - (i * 0.3), 1)
            cond = conditions[i % len(conditions)]
            chance_rain = 60 if "rain" in cond.lower() else 20
            
            forecast = f"""{day_date}:
High: {high_c}°C ({round(high_c * 9/5 + 32, 1)}°F)
Low: {low_c}°C ({round(low_c * 9/5 + 32, 1)}°F)
Condition: {cond}
Chance of Rain: {chance_rain}%
Max Wind: {mock['wind_kph'] + i*2} km/h
UV Index: {mock['uv']}"""
            forecasts.append(forecast)
        
        forecasts.append("(Note: Using simulated forecast telemetry)")
        return "\n---\n".join(forecasts)

    location = data["location"]
    forecast_days = data["forecast"]["forecastday"]
    
    forecasts = []
    forecasts.append(f"Weather Forecast for {location['name']}, {location['region']}, {location['country']}:")
    
    for day in forecast_days:
        day_data = day["day"]
        date = day["date"]
        
        forecast = f"""{date}:
High: {day_data['maxtemp_c']}°C ({day_data['maxtemp_f']}°F)
Low: {day_data['mintemp_c']}°C ({day_data['mintemp_f']}°F)
Condition: {day_data['condition']['text']}
Chance of Rain: {day_data['daily_chance_of_rain']}%
Max Wind: {day_data['maxwind_kph']} km/h
UV Index: {day_data['uv']}"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
async def health_check() -> str:
    """Health check endpoint for deployment verification."""
    return "✅ Weather MCP Server is running! Ready to provide weather data for Australian cities, Vietnamese cities, and worldwide."

print("✅ MCP server initialized with Streamable HTTP transport")
print("🔧 Available tools: get_current_weather, get_forecast, health_check")

if __name__ == "__main__":
    import sys
    
    is_cloud_run = bool(os.getenv("PORT"))
    is_standalone = len(sys.argv) == 1 and sys.stdin.isatty()
    
    if is_cloud_run or is_standalone:
        print(f"🚀 Starting MCP server on http://0.0.0.0:{port}/mcp")
        mcp.run(transport="streamable-http")
    else:
        print("Starting FastMCP server in stdio mode for local client", file=sys.stderr)
        mcp.run()