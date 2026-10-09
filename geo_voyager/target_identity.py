import json

from .observation import Observation

ID_KEYS = ('relation_id', 'id')


def _identity(item: dict):
    for key in ID_KEYS:
        if item.get(key) is not None:
            return (key, str(item[key]))
    return ('object', json.dumps(item, sort_keys=True, ensure_ascii=False))


def resolve_target(name: str, observations: tuple[Observation, ...]) -> dict | None:
    """The target named `name` in earlier Observations, matched by name and never by position.

    An Observation is a JSON list of targets or one target. Objects with the same name and the
    same id are one target seen twice. None when the name is absent, or ambiguous because
    different ids share it.
    """
    matches = []
    for observation in observations:
        try:
            value = json.loads(observation.text)
        except ValueError:
            continue
        for item in value if isinstance(value, list) else [value]:
            if isinstance(item, dict) and item.get('name') == name:
                matches.append(item)
    if not matches or len({_identity(match) for match in matches}) != 1:
        return None
    return matches[0]


def _candidates(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value] + [item for inner in value.values() if isinstance(inner, list) for item in inner]
    return []


def discover_targets(observations: tuple[Observation, ...]) -> list[dict]:
    """The targets (a name with a stable id) an earlier step made known, in the order first seen.

    Looks at a JSON object, a JSON list of objects, and lists of objects directly under an object's keys.
    Only the name and the id are kept, so a target seen again with a count attached is the same target.
    """
    found, seen = [], set()
    for observation in observations:
        try:
            value = json.loads(observation.text)
        except ValueError:
            continue
        for item in _candidates(value):
            if not isinstance(item, dict) or not isinstance(item.get('name'), str):
                continue
            key = next((key for key in ID_KEYS if item.get(key) is not None), None)
            if key is None or (item['name'], key, str(item[key])) in seen:
                continue
            seen.add((item['name'], key, str(item[key])))
            found.append({'name': item['name'], key: item[key]})
    return found
