from unittest.mock import Mock

import pytest

from geo_voyager.planner import Planner
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.critique import Critique

PLAN = '''調査項目: 対象の一覧を取得する
利用データセット: []
利用サービス:
  - yuisekin-geosparql
---
調査項目: 前段の対象を数える
利用データセット: []
利用サービス:
  - overpass'''


def test_string_goal_is_decomposed_with_strict_registered_resources():
    client = Mock(); client.generate.return_value = PLAN
    intents = Planner(client).plan('複合調査')
    assert len(intents) == 2 and all(isinstance(intent, Intent) for intent in intents)
    assert intents[0].service_ids == ('yuisekin-geosparql',)
    prompt = client.generate.call_args.args[0]
    for text in ['1 Intent = 1 measurable output', '依存関係', 'previous_observations', 'overpass', 'Dataset']:
        assert text in prompt


@pytest.mark.parametrize('reply', ['', PLAN.replace('overpass', 'unknown'), PLAN + '\n追記', PLAN.replace('利用サービス:', 'service:')])
def test_invalid_plan_is_rejected(reply):
    client = Mock(); client.generate.return_value = reply
    with pytest.raises((ValueError, KeyError)):
        Planner(client).plan('複合調査')


def test_prior_observations_are_passed_in_order_and_failed_step_stops():
    planner, executor, critic = Mock(), Mock(), Mock()
    intents = [Intent('first', service_ids=('overpass',)), Intent('second', service_ids=('overpass',))]
    planner.plan.return_value = intents
    observation = Observation('first answer')
    first = IntentExecution([observation], (), None, None, Critique(True, 'ok'), None)
    second = IntentExecution([], (), None, None, Critique(False, 'failed'), None)
    executor.execute.side_effect = [first, second]
    result = GoalExecutor(planner, executor, critic).execute('goal')
    assert executor.execute.call_args_list[1].args[0].previous_observations == (observation,)
    assert result.executions == (first, second) and not result.critique.success
    critic.check.assert_not_called()


def test_completed_goal_checks_final_output_and_reuses_updated_library():
    planner, executor, critic = Mock(), Mock(), Mock()
    learned = __import__('uuid').uuid4()
    intents = [Intent('measure first target', service_ids=('overpass',)), Intent('measure next target', service_ids=('overpass',))]
    planner.plan.return_value = intents
    first = IntentExecution([Observation('first measurement')], (), None, learned, Critique(True, 'ok'), None)
    second = IntentExecution([Observation('final answer')], (learned,), learned, None, Critique(True, 'ok'), Critique(True, 'ok'))
    executor.execute.side_effect = [first, second]
    critic.check.return_value = Critique(True, 'goal answered')
    result = GoalExecutor(planner, executor, critic).execute('goal')
    assert result.executions[1].selected_skill_id == result.executions[0].learned_skill_id
    assert result.critique.success
    assert critic.check.call_args.args[1] == first.observations + second.observations


def test_goal_prompt_requires_probe_and_small_repeatable_measurements():
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan('対象集合の測定値を比較する')
    prompt = client.generate.call_args.args[0]
    assert '1対象で方法を確立' in prompt
    assert '両方を [] にしない' in prompt
    assert '対象の名前で指定' in prompt


def test_planner_prefers_registered_graph_for_known_target_collections():
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan('対象集合を比較する')
    assert '既存 Graph に対象型が登録されている場合' in client.generate.call_args.args[0]


def test_repeated_fixed_fields_also_define_unambiguous_plan_boundaries():
    client = Mock(); client.generate.return_value = PLAN.replace('\n---\n', '\n\n')
    assert len(Planner(client).plan('複合調査')) == 2


def test_local_final_step_requires_prior_context_instead_of_dummy_service():
    client = Mock(); client.generate.return_value = PLAN + '\n---\n調査項目: 前段の件数から最大を選ぶ\n利用データセット: []\n利用サービス:'
    intents = Planner(client).plan('複合調査')
    assert len(intents) == 3 and intents[-1].requires_context
    assert intents[-1].service_ids == () and intents[-1].dataset_ids == ()


def test_single_leading_document_separator_is_allowed():
    client = Mock(); client.generate.return_value = '---\n' + PLAN
    assert len(Planner(client).plan('複合調査')) == 2


def test_final_critic_receives_all_successful_step_observations():
    planner, executor, critic = Mock(), Mock(), Mock()
    planner.plan.return_value = [Intent('一覧', service_ids=('overpass',)), Intent('最大', requires_context=True)]
    observations = [Observation('measurement evidence'), Observation('final answer')]
    executor.execute.side_effect = [IntentExecution([obs], (), None, None, Critique(True, 'ok'), None) for obs in observations]
    critic.check.return_value = Critique(True, 'complete')
    GoalExecutor(planner, executor, critic).execute('goal')
    assert critic.check.call_args.args[1] == observations


TARGET_PLAN = PLAN.replace('  - overpass', '  - overpass\n対象: 渋谷区')


def test_a_target_line_names_the_target_of_the_intent():
    client = Mock(); client.generate.return_value = TARGET_PLAN
    intents = Planner(client).plan('渋谷区のカフェ数')
    assert [intent.target_name for intent in intents] == [None, '渋谷区']


def test_an_empty_target_line_is_rejected():
    client = Mock(); client.generate.return_value = PLAN + '\n対象:'
    with pytest.raises(ValueError):
        Planner(client).plan('渋谷区のカフェ数')


def test_a_target_line_must_come_after_the_resource_lists():
    client = Mock(); client.generate.return_value = PLAN.replace('利用データセット: []', '対象: 渋谷区\n利用データセット: []', 1)
    with pytest.raises(ValueError):
        Planner(client).plan('渋谷区のカフェ数')


def test_planner_prompt_names_targets_by_identity_not_by_list_position():
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan('複数の対象を測る')
    prompt, kwargs = client.generate.call_args.args[0], client.generate.call_args.kwargs
    for removed in ['一覧のN番目', '一覧の番号1から', '番号1から件数まで']:
        assert removed not in prompt
    assert 'list position' not in kwargs['system_prompt']
    for required in ['対象の名前で指定', '対象: 名前', 'name と安定ID', 'relation_id']:
        assert required in prompt
