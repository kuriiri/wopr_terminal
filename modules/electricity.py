import datetime
import requests

BASE_URL = "https://sahkotin.fi/prices"


def classify_level(price_c):
    """
    Classify price level according to your thresholds.
    Returns one of: "GREEN", "YELLOW", "RED", "SEVERE", or "NONE".
    """
    if price_c is None:
        return "NONE"
    if price_c < 10.0:
        return "GREEN"
    if price_c < 20.0:
        return "YELLOW"
    if price_c > 50.0:
        return "SEVERE"
    if price_c > 20.0:
        return "RED"


def get_spot_prices(hours_ahead=36):
    """
    Fetch Finnish spot prices from sahkotin.fi, with VAT, in c/kWh.
    Returns a dict with:
      {
        "rows": [  # sorted from now onwards
          {
            "time": datetime (local),
            "price": float or None,
            "level": "GREEN"/"YELLOW"/"RED"/"SEVERE"/"NONE",
            "trend": "^" / "v" / "-" / " ",
            "is_current": bool,
          },
          ...
        ],
        "current_price": float or None,
        "current_level": str,
        "max_price": float or None,
        "min_price": float or None,
        "max_time": datetime or None,
        "min_time": datetime or None,
      }
    On error, returns {"rows": [], ...} with None fields.
    """

    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    # Fetch from midnight local today to cover "now + future"
    start = now.replace(hour=0)
    # sahkotin expects ISO 8601; example uses .000Z, but docs say "local time".
    # We'll send local date/time without timezone, they handle it.
    start_str = start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    url = f"{BASE_URL}?fix&vat&start={start_str}"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        raw_prices = data.get("prices", [])
    except Exception:
        return {
            "rows": [],
            "current_price": None,
            "current_level": "NONE",
            "max_price": None,
            "min_price": None,
            "max_time": None,
            "min_time": None,
        }

    rows = []

    # Build list of (local time, price) and filter for now..now+hours_ahead
    horizon = now + datetime.timedelta(hours=hours_ahead)

    for item in raw_prices:
        date_str = item.get("date")
        val = item.get("value", None)

        if not date_str:
            continue

        try:
            # incoming like "2023-12-31T22:00:00.000Z"
            dt_utc = datetime.datetime.fromisoformat(
                date_str.replace("Z", "+00:00")
            )
            dt_local = dt_utc.astimezone()  # system local zone
        except Exception:
            continue

        if dt_local < now:
            # Skip past hours — you only want now + future
            continue
        if dt_local > horizon:
            continue

        # val is already c/kWh with VAT when using fix&vat; might be None for
        # not-yet-published hours.
        price = float(val) if val is not None else None
        level = classify_level(price)

        rows.append({"time": dt_local, "price": price, "level": level})

    # Sort rows by time just in case
    rows.sort(key=lambda r: r["time"])

    if not rows:
        return {
            "rows": [],
            "current_price": None,
            "current_level": "NONE",
            "max_price": None,
            "min_price": None,
            "max_time": None,
            "min_time": None,
        }

    # Trend arrows and current flag
    prev_price = None
    max_price = None
    min_price = None
    max_time = None
    min_time = None
    now_hour = now

    for i, row in enumerate(rows):
        price = row["price"]

        # trend vs previous non-null
        if price is None or prev_price is None:
            trend = " "
        else:
            if price > prev_price + 0.05:
                trend = "^"
            elif price < prev_price - 0.05:
                trend = "v"
            else:
                trend = "-"
        row["trend"] = trend

        if price is not None:
            prev_price = price
            if (max_price is None) or (price > max_price):
                max_price = price
                max_time = row["time"]
            if (min_price is None) or (price < min_price):
                min_price = price
                min_time = row["time"]

        # current hour mark
        row["is_current"] = (row["time"] == now_hour)

    current_price = rows[0]["price"]
    current_level = rows[0]["level"]

    return {
        "rows": rows,
        "current_price": current_price,
        "current_level": current_level,
        "max_price": max_price,
        "min_price": min_price,
        "max_time": max_time,
        "min_time": min_time,
    }
