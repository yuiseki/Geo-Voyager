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
    assert critic.check.call_args.args[1] == second.observations
