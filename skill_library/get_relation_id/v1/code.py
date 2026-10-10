import json

from geo_voyager.control_primitives import call_service


def get_relation_id(intent_target):
    """Find the OSM relation of a named place (for example a ward) with Nominatim and return its name and relation_id. When the target already carries a relation_id, that id is returned without a search."""
    if intent_target.get("id_type") == "relation_id" and intent_target.get("id_value"):
        return {"name": intent_target["name"], "relation_id": str(intent_target["id_value"])}
    results = json.loads(call_service("nominatim", path="/search",
                                      params={"q": intent_target["name"], "format": "jsonv2", "limit": "10"}))
    relations = [item for item in results if item.get("osm_type") == "relation"]
    if not relations:
        raise ValueError(f"No OSM relation found for {intent_target['name']}")
    return {"name": intent_target["name"], "relation_id": str(relations[0]["osm_id"])}
