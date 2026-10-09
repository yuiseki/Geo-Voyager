import json
import re

from .observation import Observation
from .target_ref import TargetRef

ID_KEYS = ('relation_id', 'id')


def _candidates(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value] + [item for inner in value.values() if isinstance(inner, list) for item in inner]
    return []


class AmbiguousTarget(ValueError):
    """A name that stands for more than one known target. It has to be settled by an id."""


def _objects(observations: tuple[Observation, ...]) -> list[dict]:
    """The JSON objects in the observations: the value itself, the items of a list, lists under a key."""
    found = []
    for observation in observations:
        try:
            value = json.loads(observation.text)
        except ValueError:
            continue
        found.extend(item for item in _candidates(value) if isinstance(item, dict))
    return found


def _ref_of(item: dict) -> TargetRef | None:
    if not isinstance(item.get('name'), str) or not item['name'].strip():
        return None
    key = next((key for key in ID_KEYS if item.get(key) is not None), None)
    return TargetRef(item['name'], key, str(item[key])) if key else None


def discover_targets(observations: tuple[Observation, ...]) -> list[TargetRef]:
    """The targets (a name with a stable id) the observations make known, in the order first seen.

    A target is its id. The same id under two names is one target and keeps the first name. The same name
    under two ids is two targets.
    """
    found: dict[tuple, TargetRef] = {}
    for item in _objects(observations):
        ref = _ref_of(item)
        if ref is not None:
            found.setdefault(ref.key, ref)
    return list(found.values())


def resolve_target(target: TargetRef, observations: tuple[Observation, ...]) -> TargetRef | None:
    """The target in earlier observations. A resolved target is found by its id, never by its name alone.

    An unresolved target (a name only) is found by name when exactly one id carries that name; None when the
    name is absent or ambiguous.
    """
    objects = _objects(observations)
    if target.resolved:
        for item in objects:
            if str(item.get(target.id_type)) == target.id_value:
                name = item['name'] if isinstance(item.get('name'), str) and item['name'].strip() else target.name
                return TargetRef(name, target.id_type, target.id_value)
        return None
    refs = {ref.key: ref for ref in (_ref_of(item) for item in objects) if ref is not None and ref.name == target.name}
    return next(iter(refs.values())) if len(refs) == 1 else None


def identity_conflict(target: TargetRef, observations: tuple[Observation, ...]) -> str | None:
    """Why the observations are about another target than `target`, or None.

    Only a resolved target can conflict. If objects carry an id of the target's type and none of them is the
    target's id, the observations are about something else, even if a name matches. Observations without an id
    of that type say nothing here and are left to the judge.
    """
    if not target.resolved:
        return None
    carried = [str(item[target.id_type]) for item in _objects(observations) if item.get(target.id_type) is not None]
    if not carried or target.id_value in carried:
        return None
    return (f'Observation の {target.id_type} は {", ".join(dict.fromkeys(carried))} で、対象 {target.display()} の ID '
            f'{target.id_value} と一致しない。名前が同じでも ID が違えば別の対象。')


def _base(name: str) -> str:
    return re.split(r'[,、]', name, maxsplit=1)[0].strip()


def _distinct(refs: list[TargetRef]) -> list[TargetRef]:
    return list({ref.key: ref for ref in refs}.values())


def resolve_reference(text: str, known: tuple[TargetRef, ...]) -> TargetRef:
    """The target a Planner meant by `text`, taken from the targets already known.

    By id first ('relation_id=1761717', or the id alone). Then by the exact name, then by the name before the
    first comma ('港区' for '港区, 東京都, 日本'). Two ids behind one name is refused: the name can not say which.
    A name that is not known is an unresolved target, to be looked up.
    """
    text = text.strip()
    resolved = [ref for ref in known if ref.resolved]
    by_id = [ref for ref in resolved if text == ref.id_value or re.search(
        rf'{re.escape(ref.id_type)}\s*[=:：]\s*{re.escape(ref.id_value)}(?!\w)', text)]
    if by_id:
        return _distinct(by_id)[0]
    for matches in ([ref for ref in resolved if ref.name == text], [ref for ref in resolved if _base(ref.name) == _base(text)]):
        distinct = _distinct(matches)
        if len(distinct) == 1:
            return distinct[0]
        if len(distinct) > 1:
            options = '; '.join(f'{ref.id_type}={ref.id_value} ({ref.name})' for ref in distinct)
            raise AmbiguousTarget(f'Target {text!r} is ambiguous: {options}. Name the target by its ID.')
    return TargetRef(text)
