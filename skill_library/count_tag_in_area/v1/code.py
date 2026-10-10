import json

from geo_voyager.control_primitives import call_service


def count_tag_in_area(intent_target, key, value):
    """Count the OSM features (nodes, ways and relations) with the tag key=value inside the area of the target's OSM relation, with Overpass. Returns the target's name and relation_id, the tag and the count."""
    relation = get_relation_id(intent_target)
    area = int(relation["relation_id"]) + 3600000000
    query = f'[out:json][timeout:25];nwr["{key}"="{value}"](area:{area});out count;'
    payload = json.loads(call_service("overpass", path="/api/interpreter", body=query, content_type="text/plain"))
    return {"name": relation["name"], "relation_id": relation["relation_id"], "tag": f"{key}={value}",
            "count": int(payload["elements"][0]["tags"]["total"])}
