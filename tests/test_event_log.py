"""The events of a Goal are written one JSON line each and read back the same (candidate 1, stage 1).

A Goal takes 20 to 35 minutes, and its history was kept only in memory until it ended. Read back the same, the
history lets the loop go on from the next step after a stop.
"""
import json

import pytest

from geo_voyager.critique import Critique
from geo_voyager.event_log import event_from_dict, event_to_dict
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_history import FinalCriticFailure, HistoryEntry, PlannerFailure
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.target_ref import TargetRef

FULL_INTENT = Intent(
    '前段の区対の代表点を起点と終点として経路を求める', dataset_ids=('yuiseki/jp-admin-2026-09',), service_ids=('valhalla',),
    previous_observations=(Observation('[{"name": "世田谷区", "lat": 35.646481}]'), Observation('{"count": 57}')),
    requires_context=True, target=TargetRef('世田谷区', 'relation_id', '1759474'), result_name='route_km',
    inputs=('max_pair', 'pairs'), input_notes=('step 4: 最大の組', 'step 2: 隣接'))

EVENTS = [
    HistoryEntry(5, FULL_INTENT, (Observation('{"distance_km": 14.541}'),), Critique(True, '答えが出ている'), None,
                 ('route_summary@v1',), 'route_km@v1', (TargetRef('大田区', 'relation_id', '1758947'),)),
    HistoryEntry(2, Intent('区の一覧', service_ids=('overpass',)), (), Critique(False, 'Generated Python execution failed'),
                 ExecutionFailure('Generated Python execution failed', 'partial', 'Traceback\nKeyError: \'center\'', 73),
                 (), None, ()),
    HistoryEntry(1, Intent('区の名前', service_ids=('yuisekin-geosparql',), target=TargetRef('港区')), (), None,
                 ExecutionFailure('timed out', '', '', None), (), None, ()),
    PlannerFailure('ValueError: 「対象: 世田谷区と大田区」は対象の名前ではない', '調査項目: x', 5),
    FinalCriticFailure('答えそのものが無い', 6),
]


@pytest.mark.parametrize('event', EVENTS, ids=lambda event: type(event).__name__)
def test_an_event_is_read_back_the_same_through_a_json_line(event):
    line = json.dumps(event_to_dict(event), ensure_ascii=False)
    assert '\n' not in line
    assert event_from_dict(json.loads(line)) == event


def test_an_intent_with_no_inputs_declared_stays_undeclared():
    entry = HistoryEntry(1, Intent('区の名前', service_ids=('yuisekin-geosparql',)), (), None, None, (), None, ())
    assert event_from_dict(json.loads(json.dumps(event_to_dict(entry)))).intent.inputs is None


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        event_from_dict({'kind': 'something_else'})


def test_the_events_of_a_goal_run_by_the_executor_are_read_back_the_same():
    from unittest.mock import Mock
    from geo_voyager.goal_executor import GoalExecutor
    from geo_voyager.intent_execution import IntentExecution
    from geo_voyager.planner import DONE, PlannerRejected

    decisions = [Intent('区の名前と ID', service_ids=('yuisekin-geosparql',), result_name='wards', inputs=()),
                 PlannerRejected('Intent の書式が違う', 'reply'),
                 Intent('区の人口', dataset_ids=('yuiseki/jp-admin-2026-09',), result_name='pop', inputs=('wards',)),
                 DONE, DONE]
    planner = Mock(); planner.next.side_effect = decisions                       # the PlannerRejected is raised
    executor = Mock()
    executor.execute.side_effect = [
        IntentExecution([Observation('[{"name": "世田谷区", "relation_id": "1759474"}, {"name": "大田区", "relation_id": "1758947"}]')],
                        (), (), 'wards@v1', Critique(True, 'ok')),
        IntentExecution([Observation('[{"name": "世田谷区", "population": 943664}]')], (), ('wards@v1',), None, Critique(True, 'ok')),
    ]
    critic = Mock(); critic.check.side_effect = [Critique(False, '答えが無い'), Critique(True, 'ok')]
    result = GoalExecutor(planner, executor, critic).execute_adaptive('G')
    assert [type(event).__name__ for event in result.events] == [
        'HistoryEntry', 'PlannerFailure', 'HistoryEntry', 'FinalCriticFailure']
    assert result.events[0].targets                                           # the targets the step made known
    assert [event_from_dict(json.loads(json.dumps(event_to_dict(event), ensure_ascii=False)))
            for event in result.events] == list(result.events)
