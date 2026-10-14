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


# a_run6, Goal 8, steps 1 and 2: the function built its own list in a local variable named results and returned it.
# A name assigned in a function is its local variable throughout (Python's scope), so it is not the runtime value.
@pytest.mark.parametrize('code', [
    'def a(rows):\n    """A."""\n    results = []\n    for row in rows:\n        results.append(row)\n    return results\n',
    'def a(rows):\n    """A."""\n    for results in rows:\n        pass\n    return results\n',
    'def a(rows):\n    """A."""\n    with open(rows) as dataset_id:\n        return dataset_id.read()\n',
])
def test_a_local_variable_with_a_runtime_name_is_not_a_runtime_read(code):
    assert skill_shape_problems(code) == []


def test_a_runtime_value_read_beside_a_local_of_another_name_is_still_found():
    code = 'def a():\n    """A."""\n    out = []\n    out.append(results["x"])\n    return out\n'
    assert any('reads results' in item for item in skill_shape_problems(code))


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


def test_a_copy_that_moved_its_imports_into_the_function_is_still_a_copy(tmp_path):
    # Seen with the local model: the same function, with `import json` moved from the top into its body.
    from geo_voyager.skill_library import SkillLibrary
    from geo_voyager.skill_candidate import drop_copied_skills
    library = SkillLibrary(tmp_path)
    library.add('import json\n\n\ndef a(x):\n    """A."""\n    return json.dumps(x)\n')
    copy = 'def a(x):\n    import json\n    return json.dumps(x)\n'
    assert drop_copied_skills(copy, library) == ''


def test_the_service_calls_of_code_are_found():
    from geo_voyager.skill_candidate import service_calls
    code = ('def a(x):\n    """A."""\n    r = call_service("nominatim", path="/search", params={"q": x})\n'
            '    s = call_service(service_id="overpass", path="/api/interpreter", body="q")\n    return r, s')
    assert service_calls(code) == {('nominatim', '/search'), ('overpass', '/api/interpreter')}
    assert service_calls('def a():\n    """A."""\n    return 1') == set()


def test_a_runtime_value_this_intent_does_not_pass_is_found_when_the_function_reads_it():
    from geo_voyager.skill_candidate import unpassed_runtime_reads

    code = ('import json\n\n'
            'def compare_counts(intent_target, previous_observations, intent_text, tag="amenity=cafe"):\n'
            '    """比べる。"""\n'
            '    rows = [json.loads(text) for text in previous_observations]\n'
            '    return [r for r in rows if r.get(intent_target["id_type"])]\n')
    assert unpassed_runtime_reads(code, ('previous_observations', 'intent_text')) == ['intent_target']
    assert unpassed_runtime_reads(code, ('intent_target', 'previous_observations', 'intent_text')) == []


def test_an_unread_or_defaulted_runtime_parameter_is_not_a_problem():
    from geo_voyager.skill_candidate import unpassed_runtime_reads

    unread = 'def f(intent_target, previous_observations):\n    """f"""\n    return len(previous_observations)\n'
    defaulted = 'def f(previous_observations, intent_target=None):\n    """f"""\n    return intent_target or len(previous_observations)\n'
    assert unpassed_runtime_reads(unread, ('previous_observations',)) == []
    assert unpassed_runtime_reads(defaulted, ('previous_observations',)) == []


def test_called_service_ids_include_calls_whose_path_is_a_variable():
    from geo_voyager.skill_candidate import called_service_ids

    code = ('from geo_voyager.control_primitives import call_service\n\n'
            'def f(dataset_id, endpoint="/api/interpreter"):\n    """f"""\n'
            '    return call_service("overpass", path=endpoint, params={})\n')
    assert called_service_ids(code) == {'overpass'}


@pytest.mark.parametrize('body', [
    '    for text in previous_observations:\n        value = json.loads(text)\n',
    '    for value in previous_observations:\n        pass\n',
    '    key, rest = previous_observations[0].split("=")\n',
])
def test_a_function_that_overwrites_its_argument_with_another_value_is_refused(body):
    code = ('import json\n\n\ndef f(previous_observations, key="railway", value="station"):\n    """F."""\n'
            + body + '    return {"tag": f"{key}={value}"}\n')
    problems = skill_shape_problems(code)
    assert any('引数' in item and ('value' in item or 'key' in item) for item in problems), problems


def test_an_argument_rebuilt_from_itself_is_allowed():
    code = ('def f(limit="3", key=" amenity "):\n    """F."""\n    limit = int(limit)\n    key = key.strip()\n'
            '    return {"limit": limit, "key": key}\n')
    assert skill_shape_problems(code) == []


def test_an_argument_filled_in_when_it_is_missing_is_allowed():
    code = ('def f(previous_observations=None, name=None, intent_target=None):\n    """F."""\n'
            '    if previous_observations is None:\n        previous_observations = []\n'
            '    if not name:\n        name = intent_target["name"]\n'
            '    return {"n": len(previous_observations), "name": name}\n')
    assert skill_shape_problems(code) == []


from geo_voyager.skill_candidate import overpass_element_mismatch

COUNT_NWR = ('import json\nfrom geo_voyager.control_primitives import call_service\n\n'
             'def count_tag(key="amenity", value="pharmacy"):\n    """数える。"""\n'
             '    query = f\'[out:json];nwr["{key}"="{value}"](area:3601761717);out count;\'\n'
             '    return json.loads(call_service("overpass", path="/api/interpreter", params={"data": query}))\n')


def test_an_intent_about_nodes_refuses_a_query_for_every_element_type():
    # Round 3: 'amenity=pharmacy のノード件数' was counted with nwr, 211 where the nodes are 208.
    found = overpass_element_mismatch('各区の amenity=pharmacy のノード件数を数える', COUNT_NWR)
    assert found and 'nwr' in found[0] and 'node' in found[0]
    assert overpass_element_mismatch('各区の amenity=pharmacy のノード件数を数える', COUNT_NWR.replace('nwr[', 'node[')) == []


def test_an_intent_about_ways_refuses_nodes_and_every_element_type():
    assert overpass_element_mismatch('highway=primary の道路ウェイの総延長', COUNT_NWR)
    assert overpass_element_mismatch('highway=primary の道路ウェイの総延長', COUNT_NWR.replace('nwr[', 'node['))
    assert overpass_element_mismatch('highway=primary の道路ウェイの総延長', COUNT_NWR.replace('nwr[', 'way[')) == []


def test_an_intent_that_names_no_element_type_or_several_is_not_checked():
    for text in ('amenity=pharmacy の件数', 'amenity=pharmacy のノードとウェイの件数', 'amenity=pharmacy の要素のうちノード以外'):
        assert overpass_element_mismatch(text, COUNT_NWR) == [], text


def test_python_that_indexes_a_node_or_a_way_is_not_a_query():
    code = ('def lat_of(node, way):\n    """緯度。"""\n    return node["lat"], way["nodes"]\n')
    assert overpass_element_mismatch('ノードの緯度', code) == []


def test_a_relation_looked_up_by_id_for_its_area_is_not_what_is_counted():
    code = COUNT_NWR.replace('nwr["{key}"="{value}"](area:3601761717)', 'rel(1761717);map_to_area->.a;node["{key}"="{value}"](area.a)')
    assert overpass_element_mismatch('amenity=pharmacy のノード件数', code) == []
