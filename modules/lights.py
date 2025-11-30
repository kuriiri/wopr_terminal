import requests

def get_lights(base, token):
    """
    Fetch lights or switches that represent controllable light sources.
    Returns a list of:
      { "entity": entity_id, "name": friendly_name, "is_on": bool }
    """
    if not base or not token:
        return []

    url = base.rstrip("/") + "/api/states"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        lights = []
        for ent in data:
            eid = ent["entity_id"]
            domain = eid.split(".")[0]

            # Only track lights + switches
            if domain not in ("light", "switch"):
                continue

            state = ent.get("state", "")
            attrs = ent.get("attributes", {})
            name = attrs.get("friendly_name", eid)

            is_on = state.lower() == "on"

            lights.append({
                "entity": eid,
                "name": name.upper(),
                "is_on": is_on
            })

        return lights

    except Exception as e:
        return [{"name": f"Err {e}", "entity": "", "is_on": False}]


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
