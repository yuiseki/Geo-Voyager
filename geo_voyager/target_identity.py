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
