import json

from geo_voyager.control_primitives import call_service


def route_summary(origin_lat, origin_lon, destination_lat, destination_lon, costing="auto"):
    """Route between two points with Valhalla and return the length in kilometres and the time in seconds and minutes. costing is auto, pedestrian or bicycle."""
    request = {"locations": [{"lat": origin_lat, "lon": origin_lon}, {"lat": destination_lat, "lon": destination_lon}],
               "costing": costing, "units": "kilometers"}
    summary = json.loads(call_service("valhalla", path="/route", body=json.dumps(request),
                                      content_type="application/json"))["trip"]["summary"]
    return {"costing": costing, "length_km": summary["length"], "time_s": summary["time"], "time_min": summary["time"] / 60}
