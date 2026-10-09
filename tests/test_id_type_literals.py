import pytest

from geo_voyager.id_type_literals import id_type_comparisons

# The code a model wrote for a count in a ward: the id_type of the target is 'relation_id', not 'relation',
# so the branch was never taken, the area id was not made, and every count was 0.
FROM_THE_TRACE = '''
from geo_voyager.control_primitives import call_service
def get_area_id(target):
    tid = target.get("id_type")
    tid_val = target.get("id_value")
    if tid == "relation":
        return int(tid_val) + 3600000000
    return tid_val
area_id = get_area_id(intent_target)
'''


def test_the_comparison_from_the_trace_is_found():
    assert id_type_comparisons(FROM_THE_TRACE) == ["tid == 'relation'"]


@pytest.mark.parametrize('code', [
    'if intent_target["id_type"] == "relation_id":\n    pass',
    'if intent_target.get("id_type") != "relation":\n    pass',
    'if "relation" == intent_target["id_type"]:\n    pass',
    'if intent_target["id_type"] in ("relation", "relation_id"):\n    pass',
    'kind = intent_target["id_type"]\nif kind == "way":\n    pass',
    'assert intent_target["id_type"] == "relation_id"',
    'ok = target["id_type"] == "relation"',
])
def test_a_fixed_string_compared_with_the_id_type_is_found(code):
    assert id_type_comparisons(code)


@pytest.mark.parametrize('code', [
    'matches = [t for t in candidates if str(t.get(intent_target["id_type"])) == intent_target["id_value"]]',
    'key = intent_target["id_type"]\nvalue = t[key]',
    'area_id = int(intent_target["id_value"]) + 3600000000',
    'if intent_target["id_value"] == "1759477":\n    pass',
    'name = intent_target["name"]\nif name == "港区":\n    pass',
    'if x == "relation":\n    pass',
    'this is not python(',
    '',
])
def test_using_the_id_type_as_a_key_or_comparing_other_things_is_not_found(code):
    assert id_type_comparisons(code) == []
