"""As in Voyager, the model writes functions only and the environment calls the main one (the last function)."""
import json

import pytest

from geo_voyager.skill_candidate import entry_problems, entry_program

COUNT = ('import json\n\n\ndef count_cafes(intent_target, tag="amenity=cafe"):\n    """Count."""\n'
         '    return {"name": intent_target["name"], "tag": tag, "count": 3}\n')


def run(program, **runtime):
    namespace = dict(runtime)
    import io, contextlib
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(program, namespace)
    return out.getvalue().strip()


def test_the_main_function_is_called_with_the_runtime_values_it_names_and_its_result_printed_as_json():
    program = entry_program(COUNT)
    assert json.loads(run(program, intent_target={'name': '渋谷区'})) == {'name': '渋谷区', 'tag': 'amenity=cafe', 'count': 3}


def test_the_last_function_is_the_main_one():
    code = 'def helper():\n    """H."""\n    return 1\n\n\ndef main_one(dataset_id):\n    """M."""\n    return dataset_id\n'
    assert run(entry_program(code), dataset_id='d') == '"d"'


def test_a_program_with_top_level_statements_is_run_as_it_is():
    assert entry_program('print(1)') == 'print(1)'


def test_a_named_entry_is_called_when_the_code_has_no_function_left():
    # the saved Skill is linked in front of the program; here it is put there by hand
    program = COUNT + '\n\n' + entry_program('import json', entry='count_cafes')
    assert json.loads(run(program, intent_target={'name': '新宿区'}, previous_observations=None))['name'] == '新宿区'
    # and it is only given the runtime values it takes
    program = 'def f():\n    """F."""\n    return 1\n\n' + entry_program('import json', entry='f')
    assert run(program, intent_target={'name': 'x'}) == '1'


@pytest.mark.parametrize('code,problem', [
    ('def a(intent_target, key):\n    """A."""\n    return key\n', 'key'),                 # no runtime value and no default
    ('import json\nx = 1\n\ndef a():\n    """A."""\n    return 1\n', 'トップレベル'),
    ('print(1)', '関数'),
])
def test_what_the_environment_can_not_call_is_named(code, problem):
    assert any(problem in item for item in entry_problems(code))


def test_a_callable_main_function_has_no_problem():
    assert entry_problems(COUNT) == []
