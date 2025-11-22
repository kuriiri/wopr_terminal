import requests
import time

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
            "timestamp": None,
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

        # sunrise/sunset as HH:MM local
        def fmt_time(ts):
            if not ts:
                return ""
            return time.strftime("%H:%M", time.localtime(ts))

        sunrise = fmt_time(sys.get("sunrise"))
        sunset = fmt_time(sys.get("sunset"))

        return {
            "temp": temp,
            "desc": desc,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "pressure": pressure,
            "humidity": humidity,
            "clouds": cloud_pct,
            "visibility_km": visibility_km,
            "sunrise": sunrise,
            "sunset": sunset,
            "timestamp": time.time(),  # for DATA AGE on extended screen
        }

    except Exception as e:
        return {
            "temp": "ERR",
            "desc": str(e),
            "wind_speed": "",
            "wind_dir": "",
            "pressure": "",
            "humidity": "",
            "clouds": "",
            "visibility_km": "",
            "sunrise": "",
            "sunset": "",
            "timestamp": None,
        }
