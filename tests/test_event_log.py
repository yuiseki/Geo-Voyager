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


def run_goal(on_event=None):
    from unittest.mock import Mock
    from geo_voyager.goal_executor import GoalExecutor
    from geo_voyager.intent_execution import IntentExecution
    from geo_voyager.planner import DONE, PlannerRejected
    planner = Mock(); planner.next.side_effect = [
        Intent('区の名前', service_ids=('yuisekin-geosparql',), result_name='wards', inputs=()),
        PlannerRejected('書式が違う', 'reply'), DONE]
    executor = Mock(); executor.execute.side_effect = [
        IntentExecution([Observation('[{"name": "世田谷区", "relation_id": "1759474"}]')], (), (), None, Critique(True, 'ok'))]
    critic = Mock(); critic.check.return_value = Critique(True, 'ok')
    return GoalExecutor(planner, executor, critic).execute_adaptive('G', **({'on_event': on_event} if on_event else {}))


def test_the_executor_hands_over_every_event_as_it_happens():
    seen = []
    result = run_goal(seen.append)
    assert seen == list(result.events) and len(seen) == 2


def test_the_log_of_a_goal_is_its_start_its_events_as_they_happen_and_its_end(tmp_path):
    from geo_voyager.event_log import EventLog
    path = tmp_path / '001' / 'events.jsonl'
    log = EventLog(path)
    log.start('G', memory='- step 5: 実行のエラー: KeyError: center')
    result = run_goal(log.append)
    assert len(path.read_text().splitlines()) == 3                             # written before the Goal ended
    log.end(result.stop_reason, success=True)
    read = EventLog(path).read()
    assert (read.goal, read.memory, read.events, read.stop_reason, read.success) == (
        'G', '- step 5: 実行のエラー: KeyError: center', result.events, 'done', True)
    assert read.ended


def test_a_log_without_its_end_is_a_goal_that_stopped_on_the_way(tmp_path):
    from geo_voyager.event_log import EventLog
    log = EventLog(tmp_path / 'events.jsonl')
    log.start('G')
    log.append(EVENTS[3])
    read = EventLog(tmp_path / 'events.jsonl').read()
    assert not read.ended and read.events == (EVENTS[3],) and read.memory is None and read.stop_reason is None


def test_the_end_of_a_goal_keeps_how_it_stopped_and_no_critics_words(tmp_path):
    from geo_voyager.event_log import EventLog
    log = EventLog(tmp_path / 'events.jsonl')
    log.start('G')
    log.end('final_critic_failed', success=False)
    assert json.loads((tmp_path / 'events.jsonl').read_text().splitlines()[-1]) == {
        'kind': 'goal_ended', 'stop_reason': 'final_critic_failed', 'success': False}


def test_how_many_attempts_a_step_took_is_kept_in_the_step_and_read_back():
    from geo_voyager.goal_history import GoalHistory
    from geo_voyager.intent_execution import IntentExecution
    execution = IntentExecution([Observation('[{"name": "世田谷区"}]')], (), (), None, Critique(True, 'ok'), attempts=('a', 'b'))
    entry = HistoryEntry.from_execution(1, Intent('区', service_ids=('overpass',)), execution, GoalHistory())
    assert entry.attempts == 2
    assert event_from_dict(json.loads(json.dumps(event_to_dict(entry)))).attempts == 2


class Crash(Exception):
    """The process stopping on the way (a model call that times out, a SIGTERM)."""


def scripted(crash_at=None):
    """A Planner, an executor and a Critic that give the same replies however often the Goal is taken up: the
    Planner's decision depends only on how many steps the history holds, as a model at temperature zero shown the
    same history writes the same reply."""
    from unittest.mock import Mock
    from geo_voyager.intent_execution import IntentExecution
    from geo_voyager.planner import DONE, PlannerRejected
    intents = [Intent('区の名前', service_ids=('yuisekin-geosparql',), result_name='wards', inputs=()),
               Intent('区の人口', dataset_ids=('yuiseki/jp-admin-2026-09',), result_name='pop', inputs=('wards',)),
               Intent('最大の区', requires_context=True, result_name='top', inputs=('pop',))]
    outputs = ['[{"name": "世田谷区", "relation_id": "1759474"}, {"name": "大田区", "relation_id": "1758947"}]',
               '[{"name": "世田谷区", "population": 943664}, {"name": "大田区", "population": 748081}]',
               '{"name": "世田谷区", "population": 943664}']

    def next_decision(goal, history, **kwargs):
        if len(history) == 1 and not history.planner_failures():
            raise PlannerRejected('書式が違う', 'reply')
        return intents[len(history)] if len(history) < len(intents) else DONE

    def execute(intent):
        step = [i.text for i in intents].index(intent.text)
        if step == crash_at:
            raise Crash()
        return IntentExecution([Observation(outputs[step])], (), (), None, Critique(True, 'ok'), attempts=('a',))

    planner = Mock(); planner.next.side_effect = next_decision
    executor = Mock(); executor.execute.side_effect = execute
    critic = Mock(); critic.check.return_value = Critique(True, 'ok')
    return planner, executor, critic


def test_a_goal_stopped_after_its_second_step_goes_on_from_its_third_and_ends_as_if_never_stopped(tmp_path):
    from geo_voyager.event_log import EventLog
    from geo_voyager.goal_executor import GoalExecutor
    whole = GoalExecutor(*scripted()).execute_adaptive('G')

    log = EventLog(tmp_path / 'events.jsonl')
    log.start('G')
    with pytest.raises(Crash):
        GoalExecutor(*scripted(crash_at=2)).execute_adaptive('G', on_event=log.append)
    stopped = log.read()
    assert not stopped.ended and len([e for e in stopped.events if isinstance(e, HistoryEntry)]) == 2

    planner, executor, critic = scripted()
    resumed = GoalExecutor(planner, executor, critic).execute_adaptive('G', events=stopped.events, on_event=log.append)
    assert executor.execute.call_count == 1                                   # only the third step ran again
    assert resumed.events == whole.events and resumed.stop_reason == whole.stop_reason == 'done'
    log.end(resumed.stop_reason, success=True)
    assert log.read().events == whole.events                                   # the log holds each event once


def test_the_records_made_at_the_end_of_a_goal_come_out_the_same_from_its_log_alone(tmp_path):
    # Stage 4: the trace, the Exploration Graph's row and the World Graph's finding are projections of the log, so a
    # Goal taken up after a stop is recorded as if it had never stopped, and the records can be made again from logs.
    from bench.adaptive_trace import trace_events, trace_steps
    from geo_voyager.event_log import EventLog
    from geo_voyager.exploration_graph import ExplorationGraph
    from geo_voyager.goal_executor import GoalExecutor
    from geo_voyager.world_graph import WorldGraph
    log = EventLog(tmp_path / 'events.jsonl')
    log.start('G')
    result = GoalExecutor(*scripted()).execute_adaptive('G', on_event=log.append)
    log.end(result.stop_reason, success=True)
    logged = log.read()
    assert logged.history == result.history

    def records(run, name):
        world, exploration = WorldGraph(tmp_path / f'{name}_world.jsonl'), ExplorationGraph(tmp_path / f'{name}_exploration.jsonl')
        finding = world.record(run, explored_at='t')
        row = exploration.record(1, run, success=finding is not None, explored_at='t', elapsed=1.0)
        return finding, row, trace_steps(run), trace_events(run)

    from_result, from_log = records(result, 'result'), records(logged, 'log')
    assert from_log == from_result and from_log[0] is not None and from_log[1]['steps'] == 3


def test_the_start_keeps_what_the_curriculum_predicted_and_an_older_log_reads_without_it(tmp_path):
    from geo_voyager.event_log import EventLog
    log = EventLog(tmp_path / 'new.jsonl')
    log.start('G', reason='r', prediction='約 370 万人')
    assert EventLog(tmp_path / 'new.jsonl').read().prediction == '約 370 万人'
    (tmp_path / 'old.jsonl').write_text('{"kind": "goal_started", "goal": "G", "memory": null, "reason": "r"}\n')
    assert EventLog(tmp_path / 'old.jsonl').read().prediction == ''
