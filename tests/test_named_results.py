"""Each step's output is a named result, and a step declares the results it works on.

Round 7 on 27B: Observations were passed on as a list of unnamed strings, and the code joined every list it was
given (Minato, measured alone first, was counted twice), or could not tell three lists of counts apart.
"""
from unittest.mock import Mock

import pytest

from geo_voyager.critique import Critique
from geo_voyager.goal_history import GoalHistory, HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.planner import Planner, PlannerRejected

WARDS = '[{"name": "港区", "relation_id": "1761717"}, {"name": "世田谷区", "relation_id": "1759474"}]'


def planner(reply):
    client = Mock(); client.generate.return_value = reply
    return Planner(client), client


def step(number, text, obs, name=None, inputs=None, ok=True, **kwargs):
    intent = Intent(text, service_ids=('overpass',), result_name=name, inputs=inputs, **kwargs)
    return HistoryEntry(number, intent, (Observation(obs),), Critique(ok, 'ok'), None, (), None, ())


def history(*entries):
    result = GoalHistory()
    for item in entries:
        result.append(item)
    return result


LISTED = history(step(1, '23区の一覧', WARDS, name='wards'))
PHARMACY = ('調査項目: 前段の各区の amenity=pharmacy の要素数\n結果名: ward_pharmacy_counts\n入力:\n  - wards\n'
            '利用データセット: []\n利用サービス:\n  - overpass')


def test_the_planner_reads_the_result_name_and_the_inputs():
    intent = planner(PHARMACY)[0].next('薬局の数', LISTED)
    assert intent.result_name == 'ward_pharmacy_counts' and intent.inputs == ('wards',)
    assert intent.text == '前段の各区の amenity=pharmacy の要素数' and intent.service_ids == ('overpass',)


def test_the_lines_may_come_in_any_order_after_the_first():
    reply = ('調査項目: 前段の各区の amenity=pharmacy の要素数\n利用データセット: []\n利用サービス:\n  - overpass\n'
             '入力:\n  - wards\n結果名: ward_pharmacy_counts')
    intent = planner(reply)[0].next('薬局の数', LISTED)
    assert intent.result_name == 'ward_pharmacy_counts' and intent.inputs == ('wards',)


def test_an_input_that_is_no_result_is_refused_with_the_names_there_are():
    with pytest.raises(PlannerRejected) as raised:
        planner(PHARMACY.replace('  - wards', '  - ward_list'))[0].next('薬局の数', LISTED)
    assert 'ward_list' in raised.value.reason and 'wards' in raised.value.reason


def test_once_there_are_results_a_step_must_say_which_it_uses():
    reply = '調査項目: 前段の各区の amenity=pharmacy の要素数\n結果名: ward_pharmacy_counts\n利用データセット: []\n利用サービス:\n  - overpass'
    with pytest.raises(PlannerRejected) as raised:
        planner(reply)[0].next('薬局の数', LISTED)
    assert '入力:' in raised.value.reason
    assert planner(reply.replace('結果名: ward_pharmacy_counts', '結果名: ward_pharmacy_counts\n入力: []'))[0] \
        .next('薬局の数', LISTED).inputs == ()


def test_the_first_step_needs_no_inputs():
    reply = '調査項目: 23区の一覧\n結果名: wards\n利用データセット: []\n利用サービス:\n  - yuisekin-geosparql'
    assert planner(reply)[0].next('薬局の数', GoalHistory()).inputs is None


def test_a_first_step_that_names_an_input_is_refused_before_it_runs():
    # Round 9, Goal 7: the first step named tokyo_23_ward_list, which no step had made, and the run stopped with a
    # KeyError when its inputs were looked up instead of the Planner being asked again.
    reply = PHARMACY.replace('  - wards', '  - tokyo_23_ward_list')
    with pytest.raises(PlannerRejected) as raised:
        planner(reply)[0].next('薬局の数', GoalHistory())
    assert 'tokyo_23_ward_list' in raised.value.reason and '入力: []' in raised.value.reason


@pytest.mark.parametrize('name', ['Ward Counts', '区の一覧', '1wards', 'wards-list'])
def test_a_result_name_is_a_lower_case_identifier(name):
    with pytest.raises(PlannerRejected) as raised:
        planner(PHARMACY.replace('ward_pharmacy_counts', name))[0].next('薬局の数', LISTED)
    assert '結果名' in raised.value.reason


def test_a_step_that_only_works_on_results_must_name_one():
    reply = '調査項目: 前段の件数の合計\n結果名: total\n入力: []\n利用データセット: []\n利用サービス: []'
    with pytest.raises(PlannerRejected):
        planner(reply)[0].next('薬局の数', LISTED)


def test_the_prompt_lists_the_results_by_name_with_what_each_measured():
    _, client = planner(PHARMACY)
    Planner(client).next('薬局の数', history(step(1, '23区の一覧', WARDS, name='wards'),
                                             step(2, '港区の amenity=pharmacy の要素数', '{"count": 108}', name='minato_pharmacy')))
    prompt = client.generate.call_args.args[0]
    assert '結果名:' in prompt and '入力:' in prompt
    assert 'wards: 23区の一覧' in prompt and 'minato_pharmacy: 港区の amenity=pharmacy の要素数' in prompt


NAMED = Intent('人口あたりの駅', requires_context=True, result_name='ratio', inputs=('ward_population', 'ward_stations'),
               previous_observations=(Observation('[{"name": "港区", "population": 260486}]'),
                                      Observation('[{"name": "港区", "stations": 32}]')),
               input_notes=('step 3「各区の2020年国勢調査人口」（yuiseki/jp-admin-2026-09）',
                            'step 4「各区の営業中の駅の数」（yuiseki/ekidata-jp, yuiseki/jp-admin-2026-09）'))


def test_the_worker_passes_the_inputs_by_name_as_parsed_json():
    from geo_voyager.worker import injected_lines
    namespace = {}
    exec(injected_lines(NAMED), namespace)
    assert namespace['results'] == {'ward_population': [{'name': '港区', 'population': 260486}],
                                    'ward_stations': [{'name': '港区', 'stations': 32}]}


def test_a_text_that_is_not_json_is_passed_as_it_is():
    from dataclasses import replace
    from geo_voyager.worker import injected_lines
    namespace = {}
    exec(injected_lines(replace(NAMED, previous_observations=(Observation('9733276'), Observation('done')))), namespace)
    assert namespace['results'] == {'ward_population': 9733276, 'ward_stations': 'done'}


def test_the_function_is_given_the_results():
    from geo_voyager.skill_candidate import entry_program
    from geo_voyager.skill_candidate_generator import passed_runtime_values
    assert 'results' in passed_runtime_values(NAMED)
    assert "results=globals().get('results')" in entry_program('def ratio(results):\n    """比。"""\n    return 1\n')


def test_the_code_generation_prompt_shows_each_input_by_name_with_where_it_came_from():
    from stub_replies import reply_reading
    from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
    client = Mock(); client.generate.return_value = reply_reading(NAMED, '説明:\nS\n---\nコード:\n```python\ndef ratio(results):\n    """比。"""\n    return 1\n```')
    SkillCandidateGenerator(client).generate(NAMED)
    prompt = client.generate.call_args.args[0]
    assert 'results["ward_population"]' in prompt and 'step 3「各区の2020年国勢調査人口」' in prompt
    assert 'results["ward_stations"]' in prompt and '"stations"' in prompt
    assert 'decoded = [json.loads(text) for text in previous_observations]' not in prompt


def test_the_planner_is_told_not_to_add_up_the_counts_of_each_area_for_the_whole():
    # Round 8, Goals 22 and 23: the 23 wards' counts were added up, and a feature on the border of two wards was
    # counted twice (library and community_centre 1,180 against 1,179 counted once over all 23).
    client = planner('DONE')[1]
    Planner(client).next('23区の図書館の数', LISTED)
    prompt = client.generate.call_args.args[0]
    assert '区域の集まり全体の件数' in prompt and '区ごとの件数を足さない' in prompt


def test_a_census_population_is_read_from_the_boundaries_and_an_estimate_only_when_asked():
    # Round 8, Goal 1: asked for the 2020 population of the 23 wards, the step summed WorldPop (9,653,022) instead of
    # the census in jp-admin-2026-09 (9,733,276), and the Critic passed it.
    from geo_voyager.datasets import CATALOG
    by_id = {item.id: item.description for item in CATALOG}
    assert 'population は2020年国勢調査の人口' in by_id['yuiseki/jp-admin-2026-09']
    assert 'WorldPop・推計を名指ししない人口は' in by_id['yuiseki/worldpop-jp-2026-01']
