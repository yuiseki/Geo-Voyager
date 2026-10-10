from geo_voyager.control_primitives import call_service
import json

def solve():
    """Taginfoで火山のタグを検索し、そのkey/valueを用いてOverpassで日本の国境内の火山を取得し、発見したタグと火山の名前を出力する。"""
    taginfo_resp = call_service("taginfo", path="/api/4/search/by_value", params={"query": "volcano", "sortname": "count_all", "sortorder": "desc", "page": "1", "rp": "5"})
    taginfo_data = json.loads(taginfo_resp)
    candidates = taginfo_data.get("data", [])
    if not candidates:
        raise ValueError("No volcano tags found")
    best = candidates[0]
    t_key = best["key"]
    t_val = best["value"]

    nominatim_resp = call_service("nominatim", path="/search", params={"q": "Japan", "format": "jsonv2", "limit": "1"})
    nominatim_data = json.loads(nominatim_resp)
    if not nominatim_data:
        raise ValueError("Japan not found")
    japan = nominatim_data[0]
    if japan.get("osm_type") != "relation":
        raise ValueError("Japan is not a relation")
    japan_osm_id = int(japan["osm_id"])
    japan_area_id = japan_osm_id + 3600000000

    overpass_ql = f"[out:json][timeout:12];nwr[\"{t_key}\"=\"{t_val}\"](area:{japan_area_id});out body;"
    overpass_resp = call_service("overpass", path="/api/interpreter", body=overpass_ql, content_type="text/plain")
    overpass_data = json.loads(overpass_resp)
    elements = overpass_data.get("elements", [])
    if not elements:
        raise ValueError("No volcanoes found")

    results = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "Unknown")
        results.append({"tag_key": t_key, "tag_value": t_val, "name": name})
    return results

print(json.dumps(solve(), ensure_ascii=False))