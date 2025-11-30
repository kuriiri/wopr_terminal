import requests
import datetime
import xml.etree.ElementTree as ET
import time
import logging

FINAVIA_URL = "https://apigw.finavia.fi/flights/public/v0/flights/dep"

logger = logging.getLogger("flights")


def _parse_dt(t):
    if not t:
        return None
    try:
        return datetime.datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone()
    except:
        return None


def get_flights(api_key, limit=12, retries=1, backoff=1.0, debug=False):
    if not api_key:
        return [("N/A", "NO_KEY", "", "", "", "", "", "", "ERROR")]

    headers = {
        "Accept": "application/xml",
        "app_key": api_key
    }

    attempt = 0
    last_err = None
    while attempt <= retries:
        try:
            r = requests.get(FINAVIA_URL, headers=headers, timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.text)

            # detect namespace
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0].strip("{")
            ns_map = {"f": ns} if ns else {}

            flights_out = []
            now = datetime.datetime.now().astimezone()

            for fl in root.findall(".//f:flight" if ns else ".//flight", ns_map):

                def _get(tag):
                    if ns:
                        el = fl.find(f"{{{ns}}}{tag}")
                    else:
                        el = fl.find(tag)
                    return el.text.strip() if el is not None and el.text else None

                sdt = _get("sdt")
                scheduled = _parse_dt(sdt)

                actual = _parse_dt(_get("act_d"))
                status = (_get("prt") or "").upper()

                # Skip past flights
                if status.startswith("DEPART"):
                    continue
                if actual and actual < now:
                    continue
                if scheduled and scheduled < now:
                    continue

                time_str = scheduled.strftime("%H:%M") if scheduled else "??:??"

                fltnr = _get("fltnr") or "UNK"
                dest = _get("route_1") or "UNK"
                actype = _get("actype") or "UNK"
                acreg = _get("acreg") or "UNK"
                gate = _get("gate") or "--"
                park = _get("park") or "--"
                callsign = _get("callsign") or "----"

                # Determine status + estimated time
                est = _parse_dt(_get("est_d"))
                new_time_str = est.strftime("%H:%M") if est else ""

                if status.startswith("CANCEL"):
                    status_code = "CAN"
                elif est and scheduled and est > scheduled:
                    status_code = "DEL"
                else:
                    status_code = "OK"

                flights_out.append((
                    time_str, fltnr, dest, actype,
                    acreg, gate, park, callsign,
                    status_code, new_time_str
                ))

            if not flights_out:
                return [("-----", "NO DATA", "", "", "", "", "", "", "EMPTY")]

            return flights_out[:limit]

        except Exception as e:
            last_err = str(e)

        attempt += 1
        time.sleep(backoff)

    return [("ERR", last_err, "", "", "", "", "", "", "ERROR")]

def get_arrivals(api_key, limit=10):
    """
    Fetch upcoming arrivals for HEL using Finavia's public API.
    Returns a list of rows:
      [time, flt, origin, type, reg, stand, callsign, status, new_time]
    """

    if not api_key:
        return ["No API key"]

    url = "https://apigw.finavia.fi/flights/public/v0/flights/arr"
    headers = {"app_key": api_key}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        xml_text = r.text

        root = ET.fromstring(xml_text)

        # Handle XML namespace like we did for departures
        tag = root.tag  # e.g. "{http://www.finavia.fi/FlightsService.xsd}flights"
        if tag.startswith("{"):
            ns_uri = tag.split("}")[0].strip("{")
            ns = {"f": ns_uri}
        else:
            ns = {}

        arrivals = []

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # <flights><arr><body><flight>...</flight>
        if ns:
            flight_path = ".//f:arr/f:body/f:flight"
        else:
            flight_path = ".//arr/body/flight"

        for fl in root.findall(flight_path, ns):
            # --- TIME (STA preferred, fallback sdt) ---
            sta_elem = fl.find("f:sta", ns) if ns else fl.find("sta")
            sdt_elem = fl.find("f:sdt", ns) if ns else fl.find("sdt")

            t_raw = None
            if sta_elem is not None and sta_elem.text:
                t_raw = sta_elem.text
            elif sdt_elem is not None and sdt_elem.text:
                t_raw = sdt_elem.text

            if not t_raw:
                # No time, skip
                continue

            try:
                dt_utc = datetime.datetime.fromisoformat(
                    t_raw.replace("Z", "+00:00")
                )
                # Filter past arrivals
                if dt_utc < now_utc:
                    continue
                dt_local = dt_utc.astimezone()
                t_str = dt_local.strftime("%H:%M")
            except Exception:
                t_str = ""
                dt_local = None

            # --- BASIC FIELDS ---
            def get_text(tag_name):
                if ns:
                    elem = fl.find(f"f:{tag_name}", ns)
                else:
                    elem = fl.find(tag_name)
                return elem.text.strip() if elem is not None and elem.text else ""

            flt   = get_text("fltnr") or "UNK"
            origin = get_text("route_1") or "UNK"
            ac    = get_text("actype") or "UNK"
            reg   = get_text("acreg") or ""
            stand = get_text("park") or ""
            call  = get_text("callsign") or ""

            # --- STATUS / DELAYS ---
            prt = get_text("prt")

            # If flight already landed → do not show
            if prt == "Landed":
                continue

            status = "OK"
            new_time = ""

            dt_now = datetime.datetime.now(datetime.timezone.utc)

            # Estimated arrival time (ETA)
            est_a_raw = get_text("est_d")
            if est_a_raw:
                try:
                    dt_est_utc = datetime.datetime.fromisoformat(
                        est_a_raw.replace("Z", "+00:00")
                    )
                    dt_est_local = dt_est_utc.astimezone()
                    new_time = dt_est_local.strftime("%H:%M")

                    # delay check (> 2 minutes)
                    diff_min = (dt_est_utc - dt_utc).total_seconds() / 60.0
                    if diff_min > 2:
                        status = "DEL"
                except Exception:
                    new_time = ""
            else:
                new_time = ""

            # Cancelled check — FINAVIA uses e.g. "Cancelled"
            if prt == "Cancelled":  
                status = "CAN"
                new_time = ""

            # Filtering rule:
            # keep if still upcoming OR delayed even if scheduled has passed
            keep = (
                dt_utc >= dt_now or
                status == "DEL"
            )

            if not keep:
                continue

            # Row layout must match what wopr.py expects
            arrivals.append([
                t_str,    # time
                flt,      # flight number
                origin,   # origin airport
                ac,       # aircraft type
                reg,      # registration
                stand,    # stand/park
                call,     # callsign
                status,   # OK / DEL / CAN
                new_time # raw estimated time if delayed
            ])

        if not arrivals:
            return ["No arrival data"]

        return arrivals[:limit]

    except Exception as e:
        return [f"Err: {e}"]

