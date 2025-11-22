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
