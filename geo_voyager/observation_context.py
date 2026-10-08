import json

from .observation import Observation


def _shape(value, depth=0):
    if depth > 3:
        return type(value).__name__
    if isinstance(value, list):
        return [_shape(value[0], depth + 1)] if value else []
    if isinstance(value, dict):
        return {key: _shape(item, depth + 1) for key, item in value.items()}
    return type(value).__name__


def describe_observations(observations: tuple[Observation, ...]) -> str:
    shapes = []
    for index, observation in enumerate(observations):
        try:
            value = json.loads(observation.text)
        except ValueError:
            value = observation.text
        size = f' (list length={len(value)})' if isinstance(value, list) else ''
        shapes.append(f'json.loads(previous_observations[{index}]): ' + json.dumps(_shape(value), ensure_ascii=False) + size)
    return '\n'.join(shapes)
