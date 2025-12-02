import requests

def get_lights(ha_url, token, wanted=None, name_map=None):
    if not ha_url or not token:
        return []

    try:
        r = requests.get(
            f"{ha_url}/api/states",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            timeout=8
        )
        r.raise_for_status()
        data = r.json()

        rows = []
        for item in data:
            eid = item.get("entity_id", "")
            raw_state = item.get("state", "")
            ui_name = item.get("attributes", {}).get("friendly_name", eid)

            if wanted and eid not in wanted:
                continue

            is_on = (raw_state.lower() == "on")
            available = raw_state.lower() in ("on", "off")

            # Friendly config override
            pretty_name = name_map.get(eid, ui_name) if name_map else ui_name

            rows.append([eid, pretty_name,
                         "ON" if is_on else "OFF",
                         available])

        return rows

    except Exception as e:
        return [f"Err: {e}"]



def toggle_light(base, token, entity_id):
    """
    Toggle a light or switch in HA.
    """
    if not base or not token or not entity_id:
        return False

    domain = entity_id.split(".")[0]
    service = "toggle"  # works for both light.* and switch.*

    url = f"{base.rstrip('/')}/api/services/{domain}/{service}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = { "entity_id": entity_id }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=5)
        return r.status_code in (200, 202)
    except:
        return False
