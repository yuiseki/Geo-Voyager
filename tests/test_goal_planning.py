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


def test_planner_prompt_names_targets_by_identity_not_by_list_position():
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan('複数の対象を測る')
    prompt, kwargs = client.generate.call_args.args[0], client.generate.call_args.kwargs
    for removed in ['一覧のN番目', '一覧の番号1から', '番号1から件数まで']:
        assert removed not in prompt
    assert 'list position' not in kwargs['system_prompt']
    for required in ['対象の名前で指定', '対象: 名前', 'name と安定ID', 'relation_id']:
        assert required in prompt


def plan_of(*blocks):
    return '\n---\n'.join(blocks)


FIRST = '調査項目: 港区の ID を取得\n利用データセット: []\n利用サービス:\n  - yuisekin-geosparql'
SECOND = '調査項目: 港区の件数を数える\n利用データセット: []\n利用サービス:\n  - overpass'


def targets_of(reply):
    client = Mock(); client.generate.return_value = reply
    return [intent.target_name for intent in Planner(client).plan('港区の件数')]


def test_the_target_line_may_come_first_in_a_block():
    reply = plan_of('対象: 港区\n' + FIRST, '対象: 港区\n' + SECOND)
    assert targets_of(reply) == ['港区', '港区']


def test_the_target_line_may_sit_between_the_fields_or_at_the_end():
    between = '調査項目: 港区の ID を取得\n対象: 港区\n利用データセット: []\n利用サービス:\n  - yuisekin-geosparql'
    assert targets_of(plan_of(between, SECOND + '\n対象: 港区')) == ['港区', '港区']


def test_each_target_line_belongs_to_the_block_it_is_in_not_to_a_neighbour():
    reply = plan_of('対象: 港区\n' + FIRST, SECOND, '対象: 渋谷区\n' + SECOND)
    assert targets_of(reply) == ['港区', None, '渋谷区']


def test_a_full_width_colon_is_accepted_for_the_target_line():
    assert targets_of(plan_of(FIRST + '\n対象：港区', SECOND)) == ['港区', None]


def test_two_target_lines_in_one_intent_are_rejected_not_silently_resolved():
    reply = plan_of(FIRST + '\n対象: 起点\n対象: 終点', SECOND)
    client = Mock(); client.generate.return_value = reply
    with pytest.raises(ValueError, match='more than one 対象'):
        Planner(client).plan('港区の件数')


def test_leading_and_trailing_separators_are_harmless():
    assert targets_of('---\n' + plan_of(FIRST, SECOND) + '\n---') == [None, None]


def test_blocks_without_separators_are_still_split_at_each_investigation_line():
    assert targets_of(FIRST + '\n対象: 港区\n' + SECOND) == ['港区', None]


def test_the_planner_prompt_says_a_target_line_is_one_per_intent():
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan('複数の対象を測る')
    assert '「対象:」は1つの Intent につき1行だけ' in client.generate.call_args.args[0]


def test_plan_goal_prompt_is_unchanged_by_the_step_by_step_planner():
    """The text of the first-plan prompt is the contract of the old route. A golden copy guards it."""
    from pathlib import Path
    golden = Path(__file__).with_name('plan_goal_prompt.golden.txt')
    client = Mock(); client.generate.return_value = PLAN
    Planner(client).plan_goal('ゴール文')
    kwargs = client.generate.call_args.kwargs
    actual = (client.generate.call_args.args[0] + '\n=====SYSTEM\n' + kwargs['system_prompt'] + '\n=====KW\n'
              + repr({k: v for k, v in kwargs.items() if k != 'system_prompt'}))
    assert actual == golden.read_text()
