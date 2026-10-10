from geo_voyager.control_primitives import call_service
import json

def search_station_location(station_name: str) -> dict:
    resp = call_service(service_id="nominatim", path="/search", params={"q": station_name, "format": "jsonv2", "limit": "1"})
    data = json.loads(resp)
    if not data:
        raise ValueError("No results found")
    item = data[0]
    return {
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "osm_type": item["osm_type"],
        "osm_id": int(item["osm_id"])
    }

print(json.dumps(search_station_location("上野駅"), ensure_ascii=False))