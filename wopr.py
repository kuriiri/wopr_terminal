import os

os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
os.environ["SDL_RENDER_DRIVER"] = "software"
os.environ["SDL_AUDIODRIVER"] = "dummy"

os.environ["SDL_MOUSEDRV"] = "TSLIB"
os.environ["SDL_MOUSEDEV"] = "/dev/input/event2"
os.environ["SDL_NOMOUSE"] = "0"
os.environ["SDL_TOUCH_MOUSE"] = "1"
os.environ["SDL_HINT_TOUCH_MOUSE_EVENTS"] = "1"
os.environ["SDL_HINT_MOUSE_TOUCH_EVENTS"] = "1"

import pygame
import time
import json
import threading
import datetime

from modules.weather import get_weather
from modules.hsl import get_stop_times
from modules.flights import get_flights, get_arrivals
from modules.fmi import get_pedestrian_warning
from modules.electricity import get_spot_prices
from collections import deque

# load config
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "config.json")) as f:
    cfg = json.load(f)

VIEW_HSL = 0
VIEW_DEPARTURES = 1
VIEW_WEATHER_EXT = 2
VIEW_ELECTRICITY = 3
VIEW_ARRIVALS = 4
NUM_VIEWS = 5

# 0 = HSL, 1 = Flights, 2 = extended weather view, 3 = Electricity  
current_view = 0

# Pygame init
pygame.init()
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("WOPR Terminal")
pygame.mouse.set_visible(False)

# fonts
font_path = os.path.join(HERE, "fonts", "DejaVuSansMono.ttf")
if os.path.exists(font_path):
    base_font = pygame.font.Font(font_path, 18)
else:
    base_font = pygame.font.SysFont("DejaVu Sans Mono", 18)

big_font = pygame.font.Font(font_path, 22) if os.path.exists(font_path) else pygame.font.SysFont("DejaVu Sans Mono", 22)

GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
DIM_GREEN = (0, 80, 0)
YELLOW = (255, 215, 0)
RED = (255, 80, 80)
WHITE = (255, 255, 255)


# -------- BACKLIGHT / TIME WINDOW HELPERS --------

BACKLIGHT_TIMEOUT = cfg.get("backlight_timeout_min", 20) * 60 * 1000
backlight_on = True
last_temps = deque(maxlen=12)
in_greeting = False


# state
state = {
    "weather": {"temp": "N/A", "desc": "", "trend": "", "wind_speed": "", "wind_dir": None},
    "ped_warning": None,
    "buses_stop_1": ["Loading..."],
    "buses_stop_2": ["Loading..."],
    "flights": ["Loading..."],
    "arrivals": ["Loading..."],
    "electricity": None
}

lock = threading.Lock()

def updater_loop():
    global backlight_on, force_refresh, initial_refresh

    weather_interval = cfg.get("weather_interval_sec", 300)      # default 5 min
    hsl_interval = cfg.get("hsl_interval_sec", 20)               # screen ON
    hsl_interval_off = cfg.get("hsl_interval_off_sec", 40)       # screen OFF
    flight_interval = cfg.get("flight_interval_sec", 60)         # default 1 min
    energy_interval = cfg.get("energy_interval_sec", 600)  # default every 10 minutes
  
    last_weather = 0.0
    last_hsl = 0.0
    last_flights = 0.0
    last_energy = 0.0

    while True:
        now = time.time()

        # ---------- WEATHER (only when screen ON, or forced) ----------
        if backlight_on and (now - last_weather >= weather_interval or force_refresh or initial_refresh):
            w = get_weather(
                cfg.get("openweather_key"),
                cfg.get("weather_city", "Vantaa")
            )
            p = get_pedestrian_warning(cfg.get("fmi_areacode", "FI-18"))

            # track temperature history
            new_temp = w.get("temp")
            if isinstance(new_temp, (int, float)):
                last_temps.append(new_temp)

            # Compute trend from history
            if len(last_temps) >= 3:  # need a few points
                diff = last_temps[-1] - last_temps[0]
                if diff > 0.3:
                    w["trend"] = "^"
                elif diff < -0.3:
                    w["trend"] = "v"
                else:
                    w["trend"] = "-"
            else:
                w["trend"] = ""  # not enough history yet

            with lock:
                state["weather"] = w
                state["ped_warning"] = p

            last_weather = now

        # ---------- HSL BUS TIMES ----------
        # Slower interval when backlight is OFF
        this_hsl_interval = hsl_interval if backlight_on else hsl_interval_off
        if (now - last_hsl >= this_hsl_interval) or force_refresh or initial_refresh:
            b1 = get_stop_times(cfg.get("hsl_key"), cfg.get("hsl_stop_1"))
            b2 = get_stop_times(cfg.get("hsl_key"), cfg.get("hsl_stop_2"))
            with lock:
                state["buses_stop_1"] = b1
                state["buses_stop_2"] = b2
            last_hsl = now

        # ---------- FLIGHTS (only when screen ON, or forced) ----------
        if backlight_on and (now - last_flights >= flight_interval or force_refresh or initial_refresh):
            f = get_flights(cfg.get("finavia_key"))
            with lock:
                state["flights"] = f
                state["arrivals"] = get_arrivals(cfg.get("finavia_key"))
            last_flights = now

        # ---------- ELECTRICITY PRICES ----------
        if (now - last_energy >= energy_interval or force_refresh or initial_refresh):
            elec = get_spot_prices(cfg.get("electricity_hours_ahead", 36))
            with lock:
                state["electricity"] = elec
            last_energy = now
                

        # if we were asked for an immediate refresh, clear the flag now
        if force_refresh:
            force_refresh = False

        # initial run is completed
        if initial_refresh:
            initial_refresh = False
        # Do NOT turn off backlight here — override takes control
        # Simply exit initial setup without touching backlight

        time.sleep(1)

# start updater thread
t = threading.Thread(target=updater_loop, daemon=True)
t.start()

# helpers
def draw_text(text, x, y, fnt=base_font, color=GREEN):
    surf = fnt.render(str(text), True, color)
    screen.blit(surf, (x, y))

def draw_scanlines():
    for y in range(0, HEIGHT, 2):
        pygame.draw.line(screen, DIM_GREEN, (0, y), (WIDTH, y), 1)

def time_delta_str(event_time):
    """Return mission-style time delta string such as:
       '12h 55m REMAINING' or '2h 10m AGO'
    """
    if not event_time:
        return ""

    try:
        # event_time is HH:MM
        now = time.localtime()
        today_str = time.strftime("%d.%m.%Y", now)
        event_str = f"{today_str} {event_time}"

        event_struct = time.strptime(event_str, "%d.%m.%Y %H:%M")
        event_ts = time.mktime(event_struct)
        now_ts = time.time()

        delta = event_ts - now_ts
        mins = int(abs(delta) // 60)
        hrs = mins // 60
        mins = mins % 60

        if delta >= 0:
            return f"({hrs}h {mins}m REMAINING)"
        else:
            return f"({hrs}h {mins}m AGO)"
    except:
        return ""

def draw_weather_ext_view():
    """Extended weather view"""
    with lock:
        weather = state["weather"]

    city_name = cfg.get("weather_city", "Vantaa").upper()

    temp = weather.get("temp")
    trend = weather.get("trend", "")
    feels = weather.get("feels_like", None)
    pressure = weather.get("pressure", "")
    humidity = weather.get("humidity", "")
    clouds = weather.get("clouds", "")
    vis_km = weather.get("visibility_km", "")
    ws = weather.get("wind_speed", "")
    wd = weather.get("wind_dir", "")
    sunrise = weather.get("sunrise", "")
    sunset = weather.get("sunset", "")
    ts = weather.get("timestamp", None)

    # Data age (minutes)
    if isinstance(ts, (int, float)):
        age_min = int((time.time() - ts) / 60)
        age_str = f"{age_min} MIN"
    else:
        age_str = "N/A"

    # Temperature string with trend
    if isinstance(temp, (int, float)):
        temp_str = f"{temp}°C"
    else:
        temp_str = f"{temp}°C" if temp not in (None, "") else "N/A"

    if trend:
        temp_str = f"{temp_str} {trend}"

    # Feels like (optional; if not present, we skip line)
    feels_str = ""
    if isinstance(feels, (int, float)):
        feels_str = f"{feels}°C"

    # Clear screen area & title
    draw_text(f"WEATHER SYSTEM STATUS - {city_name}", 20, 70, big_font, GREEN)

    y = 110
    line_h = 26

    # TEMP
    draw_text("TEMP:",       20, y, base_font, GREEN)
    draw_text(temp_str,     180, y, base_font, GREEN)
    y += line_h

    # FEELS LIKE (only if available)
    if feels_str:
        draw_text("FEELS LIKE:", 20, y, base_font, GREEN)
        draw_text(feels_str,   180, y, base_font, GREEN)
        y += line_h

    # PRESSURE
    if pressure not in ("", None):
        draw_text("PRESSURE:",  20, y, base_font, GREEN)
        draw_text(f"{pressure} hPa", 180, y, base_font, GREEN)
        y += line_h

    # HUMIDITY
    if humidity not in ("", None):
        draw_text("HUMIDITY:",  20, y, base_font, GREEN)
        draw_text(f"{humidity} %", 180, y, base_font, GREEN)
        y += line_h

    # CLOUD COVER
    if clouds not in ("", None):
        draw_text("CLOUD COVER:", 20, y, base_font, GREEN)
        draw_text(f"{clouds} %",  180, y, base_font, GREEN)
        y += line_h

    # VISIBILITY (KM)
    if isinstance(vis_km, (int, float)):
        draw_text("VISIBILITY:", 20, y, base_font, GREEN)
        draw_text(f"{vis_km} KM", 180, y, base_font, GREEN)
        y += line_h

    # WIND SPEED
    if ws not in ("", None, "ERR"):
        draw_text("WIND SPEED:", 20, y, base_font, GREEN)
        draw_text(f"{ws} m/s",  180, y, base_font, GREEN)
        y += line_h

    # WIND DIRECTION
    if wd not in ("", None):
        draw_text("WIND DIR:", 20, y, base_font, GREEN)
        draw_text(wd,          180, y, base_font, GREEN)
        y += line_h

    # SUNRISE / SUNSET
    if sunrise:
        draw_text("SUNRISE:", 20, y, base_font, GREEN)
        delta = time_delta_str(sunrise)
        draw_text(f"{sunrise}  {delta}", 180, y, base_font, GREEN)
        y += line_h

    # SUNSET
    if sunset:
        draw_text("SUNSET:", 20, y, base_font, GREEN)
        delta = time_delta_str(sunset)
        draw_text(f"{sunset}  {delta}", 180, y, base_font, GREEN)
        y += line_h

    # DATA AGE
    draw_text("DATA AGE:",    20, y, base_font, GREEN)
    draw_text(age_str,      180, y, base_font, GREEN)

def draw_energy_view():
    """
    ENERGY PRICE STATUS – WOPR style electricity spot price view.
    Uses state["electricity"] produced by get_spot_prices().
    """
    with lock:
        elec = state.get("electricity")


    if not elec or not elec.get("rows"):
        draw_text("ENERGY PRICE STATUS", 20, 70, big_font, GREEN)
        draw_text("NO PRICE DATA", 20, 110, base_font, GREEN)
        return

    rows = elec["rows"]
    cur_price = elec.get("current_price")
    cur_level = elec.get("current_level")
    max_price = elec.get("max_price")
    min_price = elec.get("min_price")
    max_time = elec.get("max_time")
    min_time = elec.get("min_time")

    # Title
    draw_text("ENERGY PRICE STATUS", 20, 70, big_font, GREEN)

    # Current / min / max line
    y = 100
    if cur_price is not None:
        cur_str = f"{cur_price:4.1f}c"
    else:
        cur_str = "---"

    max_str = f"{max_price:4.1f}c" if max_price is not None else "---"
    min_str = f"{min_price:4.1f}c" if min_price is not None else "---"
    max_t_str = max_time.strftime("%H:%M") if max_time else "--:--"
    min_t_str = min_time.strftime("%H:%M") if min_time else "--:--"

    info_line = f"NOW {cur_str}   MIN {min_str} @ {min_t_str}   MAX {max_str} @ {max_t_str}"
    draw_text(info_line, 20, y, base_font, GREEN)
    y += 30

    # Column headers
    draw_text("TIME", 20, y, base_font, GREEN)
    draw_text("PRICE", 90, y, base_font, GREEN)
    draw_text("Δ", 170, y, base_font, GREEN)
    draw_text("BAR", 200, y, base_font, GREEN)
    y += 20

    # Determine scaling – option 1: max visible price
    prices_only = [r["price"] for r in rows if r["price"] is not None]
    if prices_only:
        scale_max = max(prices_only)
    else:
        scale_max = 1.0

    BAR_WIDTH = 26  # characters

    ticks = pygame.time.get_ticks()

    for row in rows[:14]:  # show up to 14 future hours
        dt = row["time"]
        price = row["price"]
        level = row["level"]
        trend = row.get("trend", " ")
        is_current = row.get("is_current", False)

        hh = dt.strftime("%H")
        if price is None:
            price_str = "---"
            bar_str = ""
            level_color = DIM_GREEN
        else:
            price_str = f"{price:4.1f}c"
            # scale bar height
            ratio = price / scale_max if scale_max > 0 else 0
            bar_len = max(1, int(ratio * BAR_WIDTH))
            bar_str = "#" * bar_len

            # choose color based on severity
            if level == "GREEN":
                level_color = GREEN
            elif level == "YELLOW":
                level_color = YELLOW
            elif level == "RED":
                level_color = RED
            elif level == "SEVERE":
                # flashing red
                if (ticks // 300) % 2 == 0:
                    level_color = RED
                else:
                    level_color = (120, 0, 0)
            else:
                level_color = DIM_GREEN

        # row color base
        row_color = level_color
        if price is None:
            row_color = DIM_GREEN

        # highlight current hour slightly
        if is_current:
            # little marker at TIME
            hh_display = f">{hh}<"
        else:
            hh_display = f" {hh} "

        draw_text(hh_display, 20, y, base_font, row_color)
        draw_text(price_str, 90, y, base_font, row_color)
        draw_text(trend, 170, y, base_font, row_color)
        if bar_str:
            draw_text(bar_str, 200, y, base_font, row_color)

        y += 20
        if y > 440:
            break

def draw_arrivals_view():
    draw_text("ARRIVALS HELSINKI-VANTAA", 20, 70, big_font, GREEN)
    col_y = 100

    headers = ["TIME","FLT","FROM","TYPE","REG","STD","CALLSIGN","STA","ETA"]
    cols = [20, 90, 160, 230, 300, 450, 520, 660, 720]

    for txt, x in zip(headers, cols):
        draw_text(txt, x, col_y, base_font, GREEN)

    y = col_y + 28

    with lock:
        arrs = state["arrivals"]

    for row in arrs[:10]:
        if not isinstance(row, (list, tuple)): 
            draw_text(str(row), 20, y, base_font, WHITE)
            y += 24
            continue

        t, flt, frm, ac, reg, stand, call, status, eta = row
        color = RED if status=="CAN" else YELLOW if status=="DEL" else GREEN

        data = [t, flt, frm, ac, reg, stand, call, status, eta]
        for i, (value, x) in enumerate(zip(data, cols)):
            # STATUS (index 7)
            if i == 7:
                draw_text(value, x, y, base_font, color)
            # ETA (index 8) if delayed and has new time
            elif i == 8 and status == "DEL":
                draw_text(value, x, y, base_font, YELLOW)
            # Everything else green
            else:
                draw_text(value, x, y, base_font, GREEN)
        y += 24



# -------- BACKLIGHT / TIME WINDOW HELPERS --------

def set_backlight(on: bool):
    """Control official RPi touchscreen backlight."""
    global backlight_on
    try:
        if on and not backlight_on:
            os.system("sudo sh -c 'echo 0 > /sys/class/backlight/rpi_backlight/bl_power'")
            backlight_on = True
        elif not on and backlight_on:
            os.system("sudo sh -c 'echo 1 > /sys/class/backlight/rpi_backlight/bl_power'")
            backlight_on = False
    except Exception:
        # Fail silently; app still runs even if backlight write fails
        pass

def in_on_window():
    now = time.localtime()
    current = now.tm_hour * 60 + now.tm_min

    for w in cfg.get("screen_on_windows", []):
        start_h, start_m = map(int, w["start"].split(":"))
        end_h, end_m = map(int, w["end"].split(":"))

        start = start_h * 60 + start_m
        end   = end_h * 60 + end_m

        if start <= current <= end:
            return True

    return False

def run_greeting_sequence():
    """Blocking WOPR-style greeting when waking via touch."""
    global in_greeting
    in_greeting = True

    screen.fill(BLACK)
    pygame.display.flip()
    pygame.time.delay(600)

    msg1 = "GREETINGS PROFESSOR FALKEN."
    msg2 = "HOW ARE YOU FEELING TODAY?"

    x = 20
    y1 = 140
    y2 = 180

    # Typewriter for line 1
    for ch in msg1:
        draw_text(ch, x, y1, big_font, GREEN)
        x += big_font.size(ch)[0]
        pygame.display.flip()
        pygame.time.delay(60)

    pygame.time.delay(800)

    # Typewriter for line 2
    x = 20
    for ch in msg2:
        draw_text(ch, x, y2, big_font, GREEN)
        x += big_font.size(ch)[0]
        pygame.display.flip()
        pygame.time.delay(60)

    pygame.time.delay(1200)
    in_greeting = False

# boot animation (simple)
def boot_sequence():
    screen.fill(BLACK)
    draw_text("INITIALISING WOPR TERMINAL...", 20, 40, big_font)
    pygame.display.flip()
    time.sleep(1.2)
    msg = "GREETINGS PROFESSOR FALKEN."
    x = 20
    for ch in msg:
        draw_text(ch, x, 80, big_font)
        x += big_font.size(ch)[0]
        pygame.display.flip()
        time.sleep(0.06)
    time.sleep(0.6)

boot_sequence()

# Service restart wake behavior
set_backlight(True)
last_activity = pygame.time.get_ticks()
force_refresh = True   # immediate data sync once
initial_refresh = True
overrode_schedule = True

# main loop
clock = pygame.time.Clock()

# Double-tap detection
DOUBLE_TAP_TIME = 400  # ms
last_tap_time = 0
tap_count = 0

# activity tracking for timeout
last_activity = pygame.time.get_ticks()

while True:
    now_ticks = pygame.time.get_ticks()
   
    for ev in pygame.event.get():
        ## DEBUG
        # print(ev)

        # Convert touchscreen FINGERDOWN into synthetic mouse click
        if ev.type == pygame.FINGERDOWN:
            # any finger touch counts as activity
            last_activity = now_ticks

            # If backlight is OFF, wake with greeting instead of toggling view
            if not backlight_on:
                set_backlight(True)
                pygame.event.clear()  # clear stale events
                run_greeting_sequence()
                # After greeting, we just continue to normal drawing
                force_refresh = True

                break
            else:
                mx = int(ev.x * WIDTH)
                my = int(ev.y * HEIGHT)
                pygame.event.post(
                    pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        {'pos': (mx, my), 'button': 1}
                    )
                )

        if ev.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_q, pygame.K_ESCAPE):
                pygame.quit()
                raise SystemExit
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            # Mouse or converted finger hit → activity
            last_activity = now_ticks

            # Ignore view toggling if in greeting
            if in_greeting or not backlight_on:
                continue

            # Double-tap logic
            if now_ticks - last_tap_time <= DOUBLE_TAP_TIME:
                tap_count += 1
            else:
                tap_count = 1

            last_tap_time = now_ticks

            if tap_count >= 2:
                current_view = (current_view +1 ) % NUM_VIEWS # 5 views: HSL, Flights, WX extended, Electricity, arrivals
                #show_flights = not show_flights
                tap_count = 0
    
    # ---- Backlight scheduling / timeout with override ----
    idle_ms = now_ticks - last_activity

    if overrode_schedule:
        # Ignore schedule until override timeout
        if idle_ms > BACKLIGHT_TIMEOUT:
            overrode_schedule = False
    else:
        # Normal time-based scheduling
        if in_on_window():
            set_backlight(True)
        else:
            if backlight_on and idle_ms > BACKLIGHT_TIMEOUT:
                set_backlight(False)

    # If backlight is OFF → skip drawing to prevent accidental wake flicker
    if not backlight_on:
        screen.fill(BLACK)
        pygame.display.flip()
        clock.tick(10)
        continue

    # Normal drawing when backlight is ON and not in greeting
    screen.fill(BLACK)

    # TIME top-right (always visible)
    now = time.localtime()
    dt_str = time.strftime("%d.%m.%Y %H:%M:%S", now)
    clock_text = base_font.render(dt_str, True, GREEN)
    rect = clock_text.get_rect(topright=(WIDTH - 20, 10))
    screen.blit(clock_text, rect)

    # WEATHER (always visible - now with hazard awareness)
    with lock:
        weather = state["weather"]
        ped = state.get("ped_warning")

    city = cfg.get("weather_city", "Vantaa").upper()
    temp = weather.get("temp", "N/A")
    desc = weather.get("desc", "")
    trend = weather.get("trend", "")
    wind_speed = weather.get("wind_speed", "")
    wind_dir = weather.get("wind_dir", "")  

    # Build base weather string
    weather_base = f"{city}: {temp}°C {trend}"

    # Draw base (green)
    draw_text(weather_base, 20, 40, big_font, GREEN)
    cursor_x = 20 + big_font.size(weather_base + "   ")[0]

    if ped and isinstance(ped, dict) and ped.get("type"):
        # PEDESTRIAN WARNING ACTIVE
        hazard = ped.get("type")
        until = ped.get("until")
        if until:
            hazard += f" UNTL {until}"

        # Draw weather desc first if exists
        if desc:
            d = f"—  {desc}  "
            draw_text(d, cursor_x, 40, big_font, GREEN)
            cursor_x += big_font.size(d)[0]

        # Hazard section (colored severity only)
        color = RED if ped.get("level") == "DANGER" else YELLOW
        draw_text(hazard, cursor_x, 40, big_font, color)

    else:
        # NO PEDESTRIAN WARNING — include description + wind + direction
        details = ""

        if desc:
            details += f"—  {desc}"

        # Include windspeed info if present
        if wind_speed:
            if details:
                details += "  "

            if wind_dir:
                details += f"{wind_speed} m/s {wind_dir}"
            else:
                details += f"{wind_speed} m/s"

        if details:
            draw_text(details, cursor_x, 40, big_font, GREEN)
    

    if current_view == VIEW_HSL:
        # =====================
        #   HSL BUS VIEW (table)
        # =====================
        stop1_desc = cfg.get("hsl_stop_1_desc", "").upper()
        draw_text(stop1_desc, 20, 70, big_font)
        draw_text("TIME", 20, 100, base_font, GREEN)
        draw_text("ROUTE", 120, 100, base_font, GREEN)
        draw_text("MIN", 200, 100, base_font, GREEN)
        draw_text("DEST", 260, 100, base_font, GREEN)
        draw_text("STATUS", 450, 100, base_font, GREEN)

        y = 125
        with lock:
            city_rows = state["buses_stop_1"][:5]

        if not city_rows or any("Load" in str(r) for r in city_rows):
            draw_text("Loading HSL data...", 20, y, base_font, GREEN)
            y += 26
        elif len(city_rows) == 1 and isinstance(city_rows[0], str) and "No" in city_rows[0]:
            draw_text("No upcoming departures", 20, y, base_font, GREEN)
            y += 26
        else:
            with lock:
                for row in city_rows:
                    if not (isinstance(row, (list, tuple)) and len(row) == 5):
                        continue
                    t, route, mins, dest, stat = row

                    if stat == "RUN":
                        color = RED
                        stat_txt = "RUN!!!"
                    elif stat == "DEL":
                        color = YELLOW
                        stat_txt = "DEL"
                    else:
                        color = GREEN
                        stat_txt = "OK"

                    draw_text(t,      20, y, base_font, GREEN)
                    draw_text(route, 120, y, base_font, GREEN)
                    draw_text(f"{mins:>2}",  200, y, base_font, GREEN)
                    draw_text(dest,  260, y, base_font, GREEN)
                    draw_text(stat_txt, 450, y, base_font, color)

                    y += 26

        # move down for airport direction
        y += 20
        stop2_desc = cfg.get("hsl_stop_2_desc", "").upper()
        draw_text(stop2_desc, 20, y, big_font, GREEN)
        y += 30
        draw_text("TIME", 20, y, base_font, GREEN)
        draw_text("ROUTE", 120, y, base_font, GREEN)
        draw_text("MIN", 200, y, base_font, GREEN)
        draw_text("DEST", 260, y, base_font, GREEN)
        draw_text("STATUS", 450, y, base_font, GREEN)

        y += 25

        with lock:
            air_rows = state["buses_stop_2"][:5]

        if not air_rows or any("Load" in str(r) for r in air_rows):
            draw_text("Loading HSL data...", 20, y, base_font, GREEN)
        elif len(air_rows) == 1 and isinstance(air_rows[0], str) and "No" in air_rows[0]:
            draw_text("No upcoming departures", 20, y, base_font, GREEN)
        else:
            with lock:
                for row in air_rows:
                    if not (isinstance(row, (list, tuple)) and len(row) == 5):
                        continue
                    t, route, mins, dest, stat = row

                    if stat == "RUN":
                        color = RED
                        stat_txt = "RUN!!!"
                    elif stat == "DEL":
                        color = YELLOW
                        stat_txt = "DEL"
                    else:
                        color = GREEN
                        stat_txt = "OK"

                    draw_text(t,      20, y, base_font, GREEN)
                    draw_text(route, 120, y, base_font, GREEN)
                    draw_text(f"{mins:>2}", 200, y, base_font, GREEN)
                    draw_text(dest,   260, y, base_font, GREEN)
                    draw_text(stat_txt, 450, y, base_font, color)

                    y += 26

    elif current_view == VIEW_ELECTRICITY:
        # =====================
        #   ENERGY PRICE VIEW
        # =====================
        draw_energy_view()


    elif current_view == VIEW_WEATHER_EXT:
        # =====================
        #   EXTENDED WEATHER VIEW
        # =====================
        draw_weather_ext_view()

    elif current_view == VIEW_DEPARTURES:
        # =====================
        #   DERARTING FLIGHTS BOARD VIEW
        # =====================
        header_y = 70
        column_y = 95
        draw_text("DEPARTURES HELSINKI-VANTAA", 20, header_y, big_font)

        draw_text("TIME", 20, column_y, base_font, GREEN)
        draw_text("FLT", 90, column_y, base_font, GREEN)
        draw_text("TO", 160, column_y, base_font, GREEN)
        draw_text("TYPE", 230, column_y, base_font, GREEN)
        draw_text("REG", 300, column_y, base_font, GREEN)
        draw_text("GTE", 390, column_y, base_font, GREEN)
        draw_text("STD", 450, column_y, base_font, GREEN)
        draw_text("CALLSIGN", 520, column_y, base_font, GREEN)
        draw_text("STA", 660, column_y, base_font, GREEN)
        draw_text("ETD", 720, column_y, base_font, GREEN)

        y = column_y + 30   # first flight row starts lower
        with lock:
            flights = state["flights"][:10]

        for flight in flights:
            if isinstance(flight, (list, tuple)) and len(flight) >= 10:
                (ts, flt, dst, ac, reg, gate, stand, call, status, newt) = flight

                # Flight base info (always green)
                draw_text(ts,    20, y, base_font, GREEN)
                draw_text(flt,   90, y, base_font, GREEN)
                draw_text(dst,   160, y, base_font, GREEN)
                draw_text(ac,    230, y, base_font, GREEN)
                draw_text(reg,   300, y, base_font, GREEN)
                draw_text(gate,  390, y, base_font, GREEN)
                draw_text(stand, 450, y, base_font, GREEN)
                draw_text(call,  520, y, base_font, GREEN)

                if status == "CAN":
                    color = RED
                elif status == "DEL":
                    color = YELLOW
                else:
                    color = GREEN

                draw_text(status, 660, y, base_font, color)

                if status == "DEL" and newt:
                    draw_text(newt, 720, y, base_font, YELLOW)
            else:
                draw_text(str(flight), 20, y, base_font, GREEN)

            y += 26

    elif current_view == VIEW_ARRIVALS:
        draw_arrivals_view()

    if cfg.get("show_scanlines", True):
        draw_scanlines()

    # flicker overlay (subtle)
    if cfg.get("enable_flicker", True):
        alpha = 30 + (abs((pygame.time.get_ticks() // 50) % 6 - 3) * 10)
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(alpha)
        screen.blit(overlay, (0, 0))

    pygame.display.flip()
    clock.tick(10)