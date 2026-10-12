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
