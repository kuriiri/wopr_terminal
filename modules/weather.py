import requests
import time
import datetime

def to_local_dt(ts):
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).astimezone()


def get_weather(api_key, city="Vantaa"):
    if not api_key:
        return {
            "temp": "N/A",
            "desc": "NO API KEY",
            "wind_speed": "",
            "wind_dir": "",
            "pressure": "",
            "humidity": "",
            "clouds": "",
            "visibility_km": "",
            "sunrise": "",
            "sunset": "",
            "sunrise_dt": None,
            "sunset_dt": None,
            "timestamp": None,
            "feels_like": ""   
        }

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&units=metric&appid={api_key}"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})
        sys = data.get("sys", {})

        temp = round(main.get("temp", 0.0), 1)
        feels = round(main.get("feels_like", temp), 1)
        desc = data["weather"][0]["description"].upper()

        for word in ["CLOUDS", "CLOUD", "LIGHT", "MODERATE", "INTENSITY"]:
            desc = desc.replace(word, "").strip()
        if not desc:
            desc = "OK"

        wind_speed = round(wind.get("speed", 0.0), 1)
        deg = wind.get("deg", 0) or 0
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        ix = int(((deg + 22.5) % 360) / 45)
        direction = dirs[ix]
        wind_dir = f"{deg}°{direction}"

        pressure = main.get("pressure", "")
        humidity = main.get("humidity", "")
        cloud_pct = clouds.get("all", "")
        vis_m = data.get("visibility", None)
        if isinstance(vis_m, (int, float)):
            visibility_km = round(vis_m / 1000.0, 1)
        else:
            visibility_km = ""

        # Sunrise/Sunset: both string and datetime
        sr_dt = to_local_dt(sys.get("sunrise"))
        ss_dt = to_local_dt(sys.get("sunset"))

        sunrise = sr_dt.strftime("%H:%M") if sr_dt else ""
        sunset  = ss_dt.strftime("%H:%M") if ss_dt else ""

        return {
            "temp": temp,
            "feels_like": feels,
            "desc": desc,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "pressure": pressure,
            "humidity": humidity,
            "clouds": cloud_pct,
            "visibility_km": visibility_km,
            "sunrise": sunrise,
            "sunset": sunset,
            "sunrise_dt": sr_dt,
            "sunset_dt": ss_dt,
            "timestamp": time.time(),  # for DATA AGE on extended screen
        }

    except Exception as e:
        return {
            "temp": "ERR",
            "feels_like": "ERR",
            "desc": str(e),
            "wind_speed": "",
            "wind_dir": "",
            "pressure": "",
            "humidity": "",
            "clouds": "",
            "visibility_km": "",
            "sunrise": "",
            "sunset": "",
            "sunrise_dt": sr_dt,
            "sunset_dt": ss_dt,
            "timestamp": None,
        }
