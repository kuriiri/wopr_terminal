# 🖥️ WOPR Display Terminal

*A Raspberry Pi–powered tactical display inspired by **Wargames (1983)**.*
Live bus departures, airport flight status, and real-time weather — rendered in glorious green phosphor terminal style.

“**Would you like to play a game?**”

## ✨ Features


* Live local time (WOPR green terminal style)                    
* Live OpenWeatherMap data w/ wind + weather trend arrows        
* HSL real-time bus departures from two stops (city + airport)   
* Finavia API: live flight departures (with delay/cancel colors) 
* Touchscreen toggle between views (double-tap)                  
* Automatic screen wake windows (morning + evening)              
* Auto sleep after inactivity timeout                            
* WOPR-style scanlines + CRT flicker effects                     
* Runs without X — pure KMSDRM framebuffer                       

## 📟 Display Views (Double-tap to cycle)

1️⃣ **HSL Transit View**
• upcoming departures from two predefined bus stops
• color-coded status:

* 🟩 ON-TIME
* 🟨 DELAYED
* 🟥 RUN!!! (departing in < 5min)

2️⃣ **Flight Status View**
• Helsinki-Vantaa departures
• shows aircraft type, gate, stand, callsign
• status color coded (CANCELLED / DELAYED)
• ETD shown if delayed

3️⃣ **Extended Weather View**
• detailed meteorological info
• sunrise/sunset with remaining time countdown
• atmospheric readings (humidity, pressure, visibility…)


## 📸 Screenshots

Weather:

![Alt text](/screenshots/wopr_wx.png?raw=true "Weather screen")


HSL BUS:

![Alt text](/screenshots/wopr_hsl.png?raw=true "HSL bus screen")



HEL / EFHK Departures:

![Alt text](/screenshots/wopr_flights.png?raw=true "HEL Departures")

## 🔆 Backlight Control

### **Auto-ON windows** (configurable)

```json
"screen_on_windows": [
  { "start": "07:00", "end": "09:00" },
  { "start": "16:00", "end": "18:00" }
]
```

During these times → always ON.
Outside → turns OFF after inactivity timeout (default 20 min).

Touch once → wakes screen + shows greeting.

## 🛠️ Hardware Requirements

* Raspberry Pi 3 / 4 / 5
* Raspberry Pi 7" Touch Display (DSI)
* Raspbian / Raspberry Pi OS (Bookworm)
* Network connectivity

## 🔑 API Requirements

Add your keys to:

```
config.json
```

Example:

```json
{
  "openweather_key": "YOUR_KEY",
  "weather_city": "Vantaa",
  "hsl_key": "YOUR_HSL_API_KEY",
  "hsl_stop_city": "HSL_STOP_ID",
  "hsl_stop_airport": "HSL_STOP_ID",
  "finavia_key": "YOUR_FINAVIA_API_KEY",

  "update_weather_sec": 300,
  "update_hsl_sec": 40,
  "update_flights_sec": 90,

  "screen_on_windows": [
    { "start": "07:00", "end": "09:00" },
    { "start": "16:00", "end": "18:00" }
  ],
  "backlight_timeout_sec": 1200
}
```` 

## 🚀 Install & Run

```bash
sudo apt install python3-pygame python3-requests
git clone https://github.com/YOURNAME/wopr-display.git
cd wopr-display
python3 wopr.py
```

### Optional systemd autostart

```bash
sudo cp wopr.service /etc/systemd/system/
sudo systemctl enable --now wopr.service
```



## 🙌 Credits

This project exists thanks to:

* **OpenWeatherMap API**
* **Digitransit HSL Routing API**
* **Finavia Flights API**
* **Wargames (1983)** for inspiration
