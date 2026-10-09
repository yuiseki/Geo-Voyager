from uuid import uuid4

from bench.adaptive_trace import render_trace, trace_steps
from geo_voyager.critique import Critique
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_executor import AdaptiveGoalExecution
from geo_voyager.goal_history import HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation


def execution_of(obs, ok=True, failure=None, attempts=1, learned=None, reused=None):
    return IntentExecution([Observation(obs)] if obs else [], (), reused, learned, Critique(ok, 'because'),
                           Critique(True, 'skill ok') if reused else None, failure=failure,
                           attempts=tuple(ExecutionAttempt('c', [], failure) for _ in range(attempts)))


def result():
    failure = ExecutionFailure('failed', '', 'Traceback\nKeyError: 0', 73)
    learned, reused = uuid4(), uuid4()
    first = Intent('港区の ID', service_ids=('yuisekin-geosparql',), target_name='港区')
    second = Intent('港区の件数', service_ids=('overpass',), target_name='港区')
    third = Intent('新宿区の件数', service_ids=('overpass',), target_name='新宿区')
    entries = (
        HistoryEntry(1, first, (Observation('{"name": "港区", "relation_id": "1"}'),), Critique(True, 'ok'), None, None, None,
                     ({'name': '港区', 'relation_id': '1'},)),
        HistoryEntry(2, second, (), Critique(False, 'crashed'), failure, None, None, ()),
        HistoryEntry(3, third, (Observation('{"count": 3}'),), Critique(True, 'ok'), None, reused, learned, ()),
    )
    executions = (execution_of('{"name": "港区", "relation_id": "1"}'), execution_of('', False, failure, attempts=3),
                  execution_of('{"count": 3}', learned=learned, reused=reused))
    return AdaptiveGoalExecution('目標', entries, executions, 'done', Critique(True, 'answered')), learned, reused


def test_each_step_is_summarised_with_its_outcome_targets_and_skills():
    value, learned, reused = result()
    steps = trace_steps(value, injected={2})
    assert [s['step'] for s in steps] == [1, 2, 3]
    assert steps[0]['target'] == '港区' and steps[0]['succeeded'] and steps[0]['new_targets'] == [{'name': '港区', 'relation_id': '1'}]
    assert steps[1]['succeeded'] is False and steps[1]['failure'] == 'KeyError: 0' and steps[1]['attempts'] == 3
    assert steps[1]['injected'] is True and steps[0]['injected'] is False
    assert steps[2]['reused_skill'] == str(reused)[:8] and steps[2]['learned_skill'] == str(learned)[:8]


def test_the_targets_the_planner_knew_before_each_step_are_derived_from_earlier_steps():
    value, _, _ = result()
    steps = trace_steps(value)
    assert steps[0]['known_before'] == [] and steps[1]['known_before'] == [{'name': '港区', 'relation_id': '1'}]
    assert steps[2]['known_before'] == [{'name': '港区', 'relation_id': '1'}]


def test_the_rendered_trace_names_the_stop_reason_and_each_step():
    value, _, _ = result()
    row = {'id': 'g', 'goal': '目標', 'stop_reason': 'done', 'critique': {'success': True, 'reason': 'answered'},
           'steps': trace_steps(value, injected={2}), 'max_steps': 8, 'injected_first_failure': False,
           'correct': True, 'oracle': {'count': 3}}
    text = render_trace(row)
    for part in ['stop: done', 'step 1', 'step 2', 'step 3', '港区の ID', 'KeyError: 0', '注入', '再利用', '学習']:
        assert part in text, part
