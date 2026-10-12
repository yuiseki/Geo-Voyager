import json

from geo_voyager.control_primitives import call_service


def count_tag_in_areas(areas, key, value):
    """Count the OSM features (nodes, ways and relations) with the tag key=value inside the union of several areas, each an object with an OSM relation_id (a list of wards), with one Overpass query. A feature on the border of two areas is counted once, which adding up the count of each area does not do. Returns the number of areas, the tag and the count."""
    ids = [int(area["relation_id"]) + 3600000000 for area in areas]
    if not ids:
        raise ValueError("no areas to count in")
    union = "".join(f"area(id:{area_id});" for area_id in ids)
    query = f'[out:json][timeout:25];({union})->.a;nwr["{key}"="{value}"](area.a);out count;'
    payload = json.loads(call_service("overpass", path="/api/interpreter", body=query, content_type="text/plain"))
    return {"areas": len(ids), "tag": f"{key}={value}", "count": int(payload["elements"][0]["tags"]["total"])}
