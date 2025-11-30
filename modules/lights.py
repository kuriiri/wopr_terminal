import requests

def auth_headers(cfg):
    token = cfg.get("ha_token")
    return {
        "Authorization": f"Bearer {token}",
        "content-type": "application/json",
    }

def get_lights_state(cfg):
    url = cfg.get("homeassistant_url") + "/api/states"
    lights = []
    try:
        r = requests.get(url, headers=auth_headers(cfg), timeout=5)
        r.raise_for_status()
        for ent in r.json():
            if ent["entity_id"].startswith("light."):
                eid = ent["entity_id"]
                st = ent["state"]
                is_on = st == "on"
                available = ent["attributes"].get("supported_features", None) is not None
                lights.append((eid, is_on, available))
        return lights
    except Exception:
        return []

def toggle_light(cfg, entity_id):
    base = cfg.get("homeassistant_url")
    url = f"{base}/api/services/light/toggle"
    data = {"entity_id": entity_id}
    try:
        requests.post(url, headers=auth_headers(cfg), json=data, timeout=5)
    except:
        pass
