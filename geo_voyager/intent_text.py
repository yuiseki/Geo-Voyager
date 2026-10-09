"""What an Intent's text may not say. The Planner decides what to find; how to call a service is not its business.

An Intent that names an endpoint path or a request parameter makes the Generator copy it into code. A model that
sees only part of a service description then invents endpoints, and the code fails on a path that does not exist.
The check is deterministic, so it needs no model and can be tested.
"""
from functools import lru_cache
import re

from .services import load_service_graph

# A path: a slash that does not follow a letter or digit, then segments. 'text/plain' and '2026/10/09' are not paths.
PATH = re.compile(r'(?<![A-Za-z0-9_])/[A-Za-z0-9_][A-Za-z0-9_.\-]*(?:/[A-Za-z0-9_.\-]+)*')
# Names the registered services take as request parameters (Taginfo, Nominatim, Overpass, Valhalla, GeoSPARQL).
# OSM tags such as amenity=cafe are data, not parameters, and are not in this list. Neither is 'key': Taginfo takes
# a key parameter, but key="cuisine" is also simply how an OSM tag key is written, and a model that says so is not
# naming a parameter.
API_PARAMETER_NAMES = ('limit', 'offset', 'sort', 'order', 'sort_count', 'sortname', 'sortorder', 'rp', 'page',
                       'query', 'q', 'format', 'data')
PARAMETER = re.compile(r'(?<![A-Za-z0-9_])(?:' + '|'.join(API_PARAMETER_NAMES) + r')\s*=\s*[^\s,、。)）」&]+')
CALL_DETAIL = re.compile(r'(?<![A-Za-z0-9_])(?:params|path)\s*=|\bcall_service\b')


@lru_cache(maxsize=1)
def _known_endpoint_forms() -> tuple[str, ...]:
    """The endpoints the registered services really have, also as they are often written without the leading slash."""
    forms = set()
    for service in load_service_graph().all():
        for path in PATH.findall(service.description):
            segments = path.strip('/').split('/')
            if len(segments) >= 2:
                forms.update({'/'.join(segments), '/'.join(segments[-2:])})
    return tuple(sorted(forms, key=len, reverse=True))


def api_details_in(text: str) -> list[str]:
    """The endpoint paths and request parameters named in the text, once each, in the order they appear."""
    found: list[tuple[int, int, str]] = []
    for pattern in (PATH, PARAMETER, CALL_DETAIL):
        found += [(match.start(), match.end(), match.group(0)) for match in pattern.finditer(text)]
    for form in _known_endpoint_forms():
        found += [(match.start(), match.end(), form) for match in
                  re.finditer(rf'(?<![A-Za-z0-9_/]){re.escape(form)}(?![A-Za-z0-9_])', text)]
    # a detail inside a longer one ('key/values' inside '/api/4/key/values') is the same mention
    kept = [item for item in found
            if not any(other is not item and other[0] <= item[0] and item[1] <= other[1] and (other[1] - other[0]) > (item[1] - item[0])
                       for other in found)]
    ordered, seen = [], set()
    for _, _, token in sorted(kept):
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered
