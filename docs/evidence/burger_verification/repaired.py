from geo_voyager.control_primitives import call_service
import json, re

observations = [json.loads(obs) for obs in previous_observations]
# The previous observations list contains the result of the first call (list of dicts)
# and then 23 individual counts. The first element is the list of admin units.
# We need to skip the first element which is the list of admin units,
# and process the remaining 23 elements which are the counts.
if len(observations) > 0 and isinstance(observations[0], list):
    observations = observations[1:]

assert len(observations) == 23, f"Expected 23 observations, got {len(observations)}"

max_count = -1
max_name = ""

for obs in observations:
    name = obs.get("name")
    count = obs.get("count")
    if count is not None and count > max_count:
        max_count = count
        max_name = name

assert max_count >= 0, "No valid count found"

print(json.dumps({"name": max_name, "count": max_count}))