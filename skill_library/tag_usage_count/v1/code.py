import json

from geo_voyager.control_primitives import call_service


def tag_usage_count(key, value):
    """Count how many times the OSM tag key=value is used in the whole OSM database, with Taginfo's tag statistics. Returns the tag and the count."""
    payload = json.loads(call_service("taginfo", path="/api/4/tag/stats", params={"key": key, "value": value}))
    total = [item["count"] for item in payload["data"] if item["type"] == "all"]
    if len(total) != 1:
        raise ValueError(f"Taginfo returned no total for {key}={value}")
    return {"key": key, "value": value, "count": total[0]}
