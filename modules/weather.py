import requests
import math
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
cfg_path = os.path.join(HERE, "..", "config.json")
with open(cfg_path) as f:
    cfg = json.load(f)


def get_weather(api_key):
    if not api_key:
        return {
            "temp": "N/A",
            "desc": "NO API KEY",
            "wind_speed": "",
            "wind_dir": ""
        }

    try:
        city = cfg.get("weather_city", "Vantaa")
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&units=metric&appid={api_key}"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        # Temperature to one decimal
        temp = round(data["main"]["temp"], 1)

        # Description → uppercase, trimmed
        desc = data["weather"][0]["description"].upper()
        for word in ["CLOUDS", "CLOUD", "LIGHT", "MODERATE", "INTENSITY"]:
            desc = desc.replace(word, "").strip()
        if not desc:
            desc = "OK"

        # Wind speed (m/s) to one decimal
        wind_raw = data.get("wind", {})
        wind_speed = round(wind_raw.get("speed", 0.0), 1)

        # Wind direction, e.g. "230°SW"
        deg = wind_raw.get("deg", 0)
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        ix = int(((deg + 22.5) % 360) / 45)
        direction = dirs[ix]
        wind_dir = f"{deg}°{direction}"

        return {
            "temp": temp,
            "desc": desc,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir
        }

    except Exception as e:
        return {
            "temp": "ERR",
            "desc": str(e),
            "wind_speed": "",
            "wind_dir": ""
        }