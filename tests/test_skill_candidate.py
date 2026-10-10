import pytest

from geo_voyager.skill_candidate import new_skill_code, skill_shape_problems

GOOD = '''import json
from geo_voyager.control_primitives import call_service


def count_tag_in_area(key, value, relation_id):
    """Count the features with the tag key=value in the area of an OSM relation."""
    return 1


print(json.dumps({"count": count_tag_in_area("amenity", "cafe", intent_target["id_value"])}))
'''


def test_the_new_skill_is_the_imports_and_the_function_without_the_program():
    code = new_skill_code(GOOD)
    assert code.startswith('import json\nfrom geo_voyager.control_primitives import call_service\n\n\ndef count_tag_in_area')
    assert 'print(' not in code


def test_a_program_that_only_calls_saved_skills_has_no_new_skill():
    assert new_skill_code('print(count_tag_in_area("a", "b", "1"))') is None
    assert skill_shape_problems('print(count_tag_in_area("a", "b", "1"))') == []


def test_a_good_candidate_has_no_problem():
    assert skill_shape_problems(GOOD) == []


@pytest.mark.parametrize('code,problem', [
    ('def a():\n    """A."""\n\ndef b():\n    """B."""\n', 'more than one function'),
    ('def a():\n    return 1\n', 'docstring'),
    ('def a():\n    """A."""\n    return intent_target["id_value"]\n', 'reads intent_target'),
    ('def a():\n    """A."""\n    return len(previous_observations)\n', 'reads previous_observations'),
])
def test_a_function_that_can_not_be_a_skill_is_named(code, problem):
    assert any(problem in item for item in skill_shape_problems(code))


def test_a_runtime_name_taken_as_a_parameter_is_fine():
    code = 'def a(previous_observations):\n    """A."""\n    return len(previous_observations)\n'
    assert skill_shape_problems(code) == []
