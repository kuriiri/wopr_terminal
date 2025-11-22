# 🖥️ WOPR Display Terminal

*A Raspberry Pi–powered 1983 supercomputer experience*

## 📡 Overview

This project turns a **Raspberry Pi + 7" touchscreen** into a retro **WOPR-style operations console**, inspired by *WarGames (1983)*.

It displays:

✔ Local time & date

✔ Live weather in Vantaa (OpenWeather API)

✔ Real-time bus departures (HSL Digitransit API)

✔ Helsinki-Vantaa airport departures (Finavia API)

✔ Retro terminal aesthetics + CRT flicker

✔ Touchscreen interaction

✔ Auto display sleep/wake logic

✔ Wake greeting:


> “GREETINGS PROFESSOR FALKEN. HOW ARE YOU FEELING TODAY?”



## 🛠️ Hardware Requirements

* Raspberry Pi 3/4/5
* Raspberry Pi Official **7" Touchscreen**
* Internet access (Wi-Fi or Ethernet)


## 🔌 Software Requirements

| Component                  | Version            |
| -------------------------- | ------------------ |
| Raspberry Pi OS (Bookworm) | Full KMS driver    |
| Python                     | 3.11+              |
| pygame                     | Tested 2.5.x       |
| requests                   | For REST API calls |


## 🔑 Required API Keys

Store in `config.json`:

```json
{
  "openweather_key": "YOUR_KEY_HERE",
  "hsl_key": "YOUR_KEY_HERE",
  "finavia_key": "YOUR_KEY_HERE",

  "hsl_stop_city": "HSL_STOP_ID_1",
  "hsl_stop_airport": "HSL_STOP_ID_2",

  "update_interval_sec": 20,
  "weather_interval_sec": 300,
  "hsl_interval_sec": 20,
  "hsl_interval_off_sec": 40,
  "flight_interval_sec": 60,
  "show_scanlines": true,
  "enable_flicker": true
}
```

📍 Stop IDs can be found via [Digitransit Routing API](https://digitransit.fi/en/developers/apis/1-routing-api/).

## 🔋 Power & Screen Logic

✔ Automatic **backlight ON** during:

* **07:00 → 09:00**
* **16:00 → 18:00**

✔ Turns off after **20 minutes** of inactivity

✔ Touching while off:


* Wakes backlight
* Shows **greeting**
* Immediately refreshes all data

## ✨ Features in Detail

| Feature      | Description                                                        |
| ------------ | ------------------------------------------------------------------ |
| Weather      | Temp, condition, wind (m/s + direction), **trend arrow** over time |
| HSL buses    | City + airport directions, countdown, DEL or RUN!!! warning        |
| Flights      | Future departures only, delayed/cancelled color coding             |
| Visual style | Green CRT text, scanlines, flicker overlay                         |
| Interaction  | Touchscreen double-tap toggles Bus/Flight view                     |


## ▶️ Autostart as Service

Install service file:

```bash
sudo cp wopr.service /etc/systemd/system/
sudo systemctl enable wopr.service
sudo systemctl start wopr.service
```

Restart display anytime:

```bash
sudo systemctl restart wopr.service
```


## 📸 Screenshots



## 🧠 Inspiration

> “The only winning move is not to play.”
> — WOPR, *WarGames* (1983)

This project is a nostalgic tribute to the era of “supercomputers” with blinking lights, green text, and a love for thermonuclear chess.


## ⚠️ Legal

This is a fan project.
No nuclear launch authority included.

If your Raspberry Pi asks about **global thermonuclear war**, politely decline.
