from unittest.mock import Mock

from bench.run_adaptive import EarlyDone, parse_spec
from geo_voyager.critique import Critique
from geo_voyager.goal_history import GoalHistory, HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.planner import DONE


def history_with(*texts):
    history = GoalHistory()
    for number, text in enumerate(texts, start=1):
        history.append(HistoryEntry(number, Intent(f'step {number}', service_ids=('overpass',)), (Observation(text),),
                                    Critique(True, 'ok'), None, None, None, ()))
    return history


def test_early_done_waits_for_a_step_that_produced_a_count_and_then_says_done_once():
    inner = Mock(); inner.next.return_value = Intent('next', service_ids=('overpass',))
    planner = EarlyDone(inner)
    assert planner.next('g', GoalHistory()) is inner.next.return_value
    assert planner.next('g', history_with('{"name": "渋谷区", "relation_id": "1"}')) is inner.next.return_value
    assert planner.injected is False
    assert planner.next('g', history_with('{"name": "渋谷区", "relation_id": "1", "count": 459}')) is DONE
    assert planner.injected is True
    assert planner.next('g', history_with('{"count": 1}')) is inner.next.return_value      # only once


def test_early_done_does_not_call_the_model_when_it_injects():
    inner = Mock()
    EarlyDone(inner).next('g', history_with('{"count": 3}'))
    inner.next.assert_not_called()


def test_the_spec_accepts_the_early_done_option():
    assert parse_spec('cafe_shibuya_vs_shinjuku:earlydone')['earlydone'] is True
    assert parse_spec('cafe_shibuya_vs_shinjuku')['earlydone'] is False
    assert parse_spec('g:inject:max=3:earlydone') == {'goal_id': 'g', 'inject': True, 'max_steps': 3, 'earlydone': True}
