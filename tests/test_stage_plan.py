"""The first stage of a staged run: the Planner's first step for every Goal, taken by the same loop as a full run
but stopped where the step would be executed."""
from unittest.mock import Mock

from bench.stage_plan import first_step
from geo_voyager.critique import Critique
from geo_voyager.intent import Intent
from geo_voyager.planner import PlannerRejected
from geo_voyager.target_ref import TargetRef

INTENT = Intent('渋谷区の relation ID を取得する', service_ids=('nominatim',), target=TargetRef('渋谷区'), result_name='shibuya_id')


def planner(*replies):
    mock = Mock(); mock.next.side_effect = list(replies)
    return mock


def test_the_intent_that_would_be_executed_is_kept_and_nothing_is_executed():
    record = first_step('渋谷区の cafe の数', planner(INTENT), Mock())
    assert record['outcome'] == 'intent' and record['planner_failures'] == []
    assert record['intent'] == {'text': '渋谷区の relation ID を取得する', 'dataset_ids': [], 'service_ids': ['nominatim'],
                                'target': {'name': '渋谷区'}, 'result_name': 'shibuya_id', 'inputs': None}


def test_a_rejected_reply_is_planned_again_as_in_a_full_run_and_the_reason_is_kept():
    record = first_step('渋谷区の cafe の数', planner(PlannerRejected('対象: が実体でない', 'reply'), INTENT), Mock())
    assert record['outcome'] == 'intent' and record['planner_failures'] == ['対象: が実体でない']


def test_a_goal_whose_first_step_never_comes_is_recorded_with_the_stop():
    from geo_voyager.goal_executor import DEFAULT_MAX_PLANNER_FAILURES
    reasons = [f'形式が違う {number}' for number in range(DEFAULT_MAX_PLANNER_FAILURES)]
    replies = [PlannerRejected(reason, 'reply') for reason in reasons]
    record = first_step('渋谷区の cafe の数', planner(*replies), Mock(check=Mock(return_value=Critique(False, 'x'))))
    assert record['outcome'] == 'planner_failure' and record['intent'] is None
    assert record['planner_failures'] == reasons
