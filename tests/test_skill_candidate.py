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
    assert skill_shape_problems('print(count_tag_in_area("a", "b", "1"))', shown=('count_tag_in_area',)) == []


def test_a_good_candidate_has_no_problem():
    assert skill_shape_problems(GOOD) == []


@pytest.mark.parametrize('code,problem', [
    ('def a():\n    """A."""\n\ndef b():\n    """B."""\n', 'more than one function'),
    ('def a():\n    """A."""\n    return intent_target["id_value"]\n', 'reads intent_target'),
    ('def a():\n    """A."""\n    return len(previous_observations)\n', 'reads previous_observations'),
])
def test_a_function_that_can_not_be_a_skill_is_named(code, problem):
    assert any(problem in item for item in skill_shape_problems(code))


def test_a_runtime_name_taken_as_a_parameter_is_fine():
    code = 'def a(previous_observations):\n    """A."""\n    return len(previous_observations)\n'
    assert skill_shape_problems(code) == []


# ---- a function must return its result, and code must either call a shown Skill or define a function

def test_a_function_that_only_prints_is_named():
    code = 'def a(x):\n    """A."""\n    print(x)\n\na(1)'
    assert any('return' in item for item in skill_shape_problems(code))


def test_a_function_that_returns_a_value_is_fine_even_if_a_nested_one_does_not():
    code = 'def a(x):\n    """A."""\n    def inner():\n        print(x)\n    inner()\n    return x\n\nprint(a(1))'
    assert skill_shape_problems(code) == []


def test_code_without_a_function_must_call_a_shown_skill():
    assert any('関数' in item for item in skill_shape_problems('print(1)', shown=('count_tags',)))
    assert skill_shape_problems('print(count_tags("a"))', shown=('count_tags',)) == []
    assert skill_shape_problems('print(1)') != []          # nothing shown: a function is required all the same


def test_a_program_with_a_syntax_error_is_left_to_the_run():
    assert skill_shape_problems('def (:', shown=()) == []


# ---- a copied definition of a saved Skill is turned back into a call

def test_a_copied_saved_skill_is_dropped_so_the_saved_one_is_called(tmp_path):
    from geo_voyager.skill_library import SkillLibrary
    from geo_voyager.skill_candidate import drop_copied_skills
    library = SkillLibrary(tmp_path)
    saved = 'import json\n\n\ndef a(x):\n    """A."""\n    return x + 1\n'
    library.add(saved)
    copied = 'import json\n\ndef a(x):\n    """A."""\n    return x + 1\n\nprint(json.dumps(a(1)))'
    assert drop_copied_skills(copied, library) == 'import json\n\nprint(json.dumps(a(1)))'


def test_a_changed_definition_of_a_saved_name_is_kept_as_a_new_version(tmp_path):
    from geo_voyager.skill_library import SkillLibrary
    from geo_voyager.skill_candidate import drop_copied_skills
    library = SkillLibrary(tmp_path)
    library.add('def a(x):\n    """A."""\n    return x + 1\n')
    changed = 'def a(x):\n    """A."""\n    return x + 2\n\nprint(a(1))'
    assert drop_copied_skills(changed, library) == changed


def test_a_copy_that_differs_only_in_comments_and_blank_lines_is_still_a_copy(tmp_path):
    from geo_voyager.skill_library import SkillLibrary
    from geo_voyager.skill_candidate import drop_copied_skills
    library = SkillLibrary(tmp_path)
    library.add('def a(x):\n    """A."""\n    return x + 1\n')
    copied = 'def a(x):\n    """A."""\n\n    # add one\n    return x + 1\nprint(a(1))'
    assert drop_copied_skills(copied, library) == 'print(a(1))'


def test_a_function_without_a_docstring_takes_the_candidates_description():
    code = 'import json\n\n\ndef a(x):\n    return x\n\n\nprint(a(1))'
    assert skill_shape_problems(code) == []                         # the description fills the docstring
    saved = new_skill_code(code, description='Return x unchanged.')
    assert '"""Return x unchanged."""' in saved and saved.startswith('import json')
    from geo_voyager.skill_function import parse_skill
    assert parse_skill(saved).description == 'Return x unchanged.'


def test_a_function_with_a_docstring_keeps_it():
    code = 'def a(x):\n    """Own words."""\n    return x\n\nprint(a(1))'
    assert parse_skill_description(new_skill_code(code, description='other')) == 'Own words.'


def parse_skill_description(code):
    from geo_voyager.skill_function import parse_skill
    return parse_skill(code).description


def test_a_copy_without_the_docstring_or_with_another_is_still_a_copy(tmp_path):
    # Seen with the local model: it copies a shown Skill without its docstring, and the description it writes
    # this time, put in as the docstring, differs from the saved one.
    from geo_voyager.skill_library import SkillLibrary
    from geo_voyager.skill_candidate import drop_copied_skills
    library = SkillLibrary(tmp_path)
    library.add('def a(x):\n    """Saved words."""\n    return x + 1\n')
    for copy in ('def a(x):\n    return x + 1\n\nprint(a(1))', 'def a(x):\n    """Other words."""\n    return x + 1\n\nprint(a(1))'):
        assert drop_copied_skills(copy, library) == 'print(a(1))'
