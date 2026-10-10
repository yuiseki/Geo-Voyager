import pytest

from geo_voyager.skill_function import parse_skill

COUNT = '''import json
from geo_voyager.control_primitives import call_service


def count_tag_in_area(key: str, value: str, relation_id: str) -> int:
    """Count the OSM features with the tag key=value inside the area of an OSM relation."""
    area = int(relation_id) + 3600000000
    query = f'[out:json][timeout:12];nwr["{key}"="{value}"](area:{area});out count;'
    payload = json.loads(call_service("overpass", path="/api/interpreter", body=query, content_type="text/plain"))
    return int(payload["elements"][0]["tags"]["total"])
'''

COMPARE = '''def compare_tags_in_area(relation_id, first, second):
    """Count two tags in one area and say which is more common."""
    counts = {tag: count_tag_in_area(*tag.split("="), relation_id) for tag in (first, second)}
    return {"counts": counts, "winner": max(counts, key=counts.get)}
'''


def test_a_skill_is_one_named_function_with_a_docstring():
    skill = parse_skill(COUNT)
    assert skill.name == 'count_tag_in_area'
    assert skill.parameters == ('key', 'value', 'relation_id')
    assert skill.description == 'Count the OSM features with the tag key=value inside the area of an OSM relation.'
    assert skill.code == COUNT.strip()


def test_the_names_a_skill_calls_are_found_without_builtins_or_its_own_names():
    assert parse_skill(COMPARE).calls == ('count_tag_in_area',)
    assert parse_skill(COUNT).calls == ('call_service',)        # a primitive is a call too; the linker tells them apart


@pytest.mark.parametrize('code,message', [
    ('print("top-level code")', 'one function'),
    ('def a():\n    """A."""\n\ndef b():\n    """B."""', 'one function'),
    ('import json\nx = 1\n\ndef a():\n    """A."""', 'only imports'),
    ('def a():\n    return 1', 'docstring'),
    ('def _private():\n    """A."""', 'name'),
    ('async def a():\n    """A."""', 'one function'),
    ('class A:\n    """A."""', 'one function'),
    ('def a(:', 'parse'),
])
def test_what_is_not_a_skill_is_refused_with_the_reason(code, message):
    with pytest.raises(ValueError, match=message):
        parse_skill(code)


def test_a_skill_may_take_keyword_only_and_defaulted_parameters():
    skill = parse_skill('def a(x, y=2, *, z=3):\n    """A."""\n    return x + y + z')
    assert skill.parameters == ('x', 'y', 'z')
