import requests
import datetime

GRAPHQL_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"

def get_stop_times(api_key, stop_id, limit=6):
    if not api_key:
        return [("N/A", "N/A", 0, "NoKey", "ERR")]
    if not stop_id:
        return [("N/A", "N/A", 0, "NoID", "ERR")]

    query = """
    {
      stop(id: "%s") {
        name
        stoptimesWithoutPatterns(numberOfDepartures: %d) {
          scheduledDeparture
          realtimeDeparture
          realtime
          serviceDay
          trip {
            routeShortName
            tripHeadsign
          }
        }
      }
    }
    """ % (stop_id, limit)

    headers = {
        "Content-Type": "application/json",
        "digitransit-subscription-key": api_key
    }

    try:
        resp = requests.post(GRAPHQL_URL, json={'query': query}, headers=headers, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        stop = data.get("data", {}).get("stop")
        if not stop:
            return [("N/A", "N/A", 0, "NoStop", "ERR")]

        rows = []
        now = datetime.datetime.now().timestamp()

        for s in stop.get("stoptimesWithoutPatterns", []):
            sched = s["serviceDay"] + s["scheduledDeparture"]
            if sched < now:
                continue  # skip past

            dt = datetime.datetime.fromtimestamp(sched)
            time_str = dt.strftime("%H:%M")

            mins = int((sched - now) / 60)

            route = s["trip"]["routeShortName"]
            headsign = s["trip"]["tripHeadsign"].split(",")[0].split("/")[0]

            realdep = s.get("realtimeDeparture", s["scheduledDeparture"]) + s["serviceDay"]
            delay = (realdep - sched) / 60.0

            if mins < 5:
                status = "RUN"
            elif delay > 1.5:
                status = "DEL"
            else:
                status = "OK"

            rows.append((time_str, route, mins, headsign, status))

        if not rows:
            return [("-----", "--", 0, "N/A", "NONE")]

        return rows[:limit]

    except Exception as e:
        return [(f"ERR", "----", 0, str(e), "ERR")]
