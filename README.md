# 🖥️ WOPR Display Terminal

*A Raspberry Pi–powered tactical display inspired by **Wargames (1983)**.*
Live bus departures, airport flight status, real-time weather and tactical weather intelligence. — rendered in glorious green phosphor terminal style.

![WOPR](https://img.shields.io/badge/WOPR-System%20Online-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%203/4-red)

## ✨ Features

🔥 **Real-time situational awareness** for the modern civilian bunker:

* Live OpenWeatherMap data w/ wind + weather trend arrows
* FMI Pedestrian-safety warning
* HSL real-time bus departures from two stops (city + airport)   
* Finavia API: live flight departures (with delay/cancel colors) 
* Spot price of electricity
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

Touch once → wakes screen

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
  "weather_city": "Vantaa,FI",
  "openweather_key": "your_openweather_api_key_here",
  "finavia_key": "your_finavia_api_key_here",
  "hsl_key": "your_hsl_api_key_here",
  "hsl_stop_1": "HSL:1234567",
  "hsl_stop_1_desc": "BUSES TO THE CITY",
  "hsl_stop_2": "HSL:1234567",
  "hsl_stop_2_desc": "BUSES TO THE AIRPORT", 
  "weather_interval_sec": 300,
  "hsl_interval_sec": 20,
  "hsl_interval_off_sec": 40,
  "flight_interval_sec": 60,
  "update_interval_sec": 20,
  "use_fahrenheit": false,
  "show_scanlines": false,
  "enable_flicker": false,
  "screen_on_windows": [
    { "start": "07:00", "end": "09:00" },
    { "start": "16:00", "end": "18:00" }
  ],
  "backlight_timeout_min": 20,
  "fmi_areacode": "FI-18",
  "electricity_hours_ahead": 36
}
```` 
Get your fmi_areacode from https://fi.wikipedia.org/wiki/ISO_3166-2:FI

## 🚀 Install & Run

```bash
sudo apt install python3-pygame python3-requests
git clone https://github.com/kuriiri/wopr_terminal_.git
cd wopr_terminal
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
* **Sähkotin API**
* **Wargames (1983)** for inspiration

## 📜 License 

Copyright (c) 2025 kuriiri

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
