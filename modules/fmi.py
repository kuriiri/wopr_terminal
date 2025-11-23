import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

CAP_FEED = "https://alerts.fmi.fi/cap/feed/atom_fi-FI.xml"

# Keywords indicating pedestrian hazards
HAZARD_KEYWORDS = [
    "slippery",
    "ice",
    "snow",
    "water on ice",
    "packed snow",
    "dry snow on ice",
]

def get_pedestrian_warning(area_code):
    """
    Returns warning dict or None:
    {
        "type": "Slippery Surface",
        "level": "DANGER" / "WATCH",
        "until": "HH:MM"
    }
    """
    try:
        r = requests.get(CAP_FEED, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.text)

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "cap": "urn:oasis:names:tc:emergency:cap:1.2"
        }

        for entry in root.findall("atom:entry", ns):
            # check area
            geos = entry.findall(".//cap:geocode", ns)
            if not any(area_code in (c.text or "") for g in geos for c in g):
                continue

            # headline text
            headline_elem = entry.find(".//cap:headline", ns)
            headline = headline_elem.text.lower() if headline_elem is not None else ""
            if not any(k in headline for k in HAZARD_KEYWORDS):
                continue

            # severity mapping
            sev_elem = entry.find(".//cap:severity", ns)
            severity = sev_elem.text.upper() if sev_elem is not None else "UNKNOWN"
            level = "DANGER" if severity in ("SEVERE", "EXTREME") else "WATCH"

            # expiration
            exp_elem = entry.find(".//cap:expires", ns)
            until_str = None
            if exp_elem is not None:
                dt = datetime.fromisoformat(exp_elem.text.replace("Z", "+00:00"))
                local = dt.astimezone()
                until_str = local.strftime("%H:%M")

            nice_text = headline.title()

            return {
                "type": nice_text,
                "level": level,
                "until": until_str
            }

        return None

    except Exception as e:
        return {"type": f"Err {e}", "level": "WATCH", "until": None}
