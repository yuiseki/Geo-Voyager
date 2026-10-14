"""The Exploration Graph keeps, for the next try of a Goal, only the failures checked without a model (ADR 0011).

A raw record given to the Planner carried a Critic's wrong rejection (港区 and 目黒区 do not touch) into the next
try, where it became a requirement of an Intent. A Critic's verdict, an Observation, the stdout of a run and the
Planner's reply must not reach the next Planner: the record has no field for them.
"""
import dataclasses
import json
from unittest.mock import Mock

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.exploration_graph import CheckedFailure, ExplorationGraph, checked_failures, outcome
from geo_voyager.goal_executor import AdaptiveGoalExecution
from geo_voyager.goal_history import FinalCriticFailure, GoalHistory, HistoryEntry, PlannerFailure
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.planner import Planner

SECRETS = ('CRITIC_SECRET', 'OBSERVATION_SECRET', 'STDOUT_SECRET', 'REPLY_SECRET', 'FINAL_SECRET', 'STEP_CRITIC_SECRET')


def entry(step, text, *, failure=None, critique=None, observations=()):
    return HistoryEntry(step, Intent(text, service_ids=('overpass',)), tuple(observations), critique, failure, (), None, ())


def failure(message, stderr, stdout=''):
    return ExecutionFailure(message, stdout, stderr, 73)


EVENTS = (
    # accepted by the Critic: a judgement and an unchecked value
    entry(1, '区の一覧', critique=Critique(True, 'STEP_CRITIC_SECRET'), observations=[Observation('OBSERVATION_SECRET')]),
    # rejected by the Critic after it ran: a judgement only
    entry(2, '隣接する区対', critique=Critique(False, 'CRITIC_SECRET 港区と目黒区の組が無い'),
          observations=[Observation('[{"a": "OBSERVATION_SECRET"}]')]),
    PlannerFailure('Intent の調査項目に API の詳細が書かれている: out geom', 'REPLY_SECRET', 2),
    entry(3, '歩道を数える', failure=failure('Generated Python execution failed', 'Traceback\n  File "<candidate>"\nKeyError: \'name\'',
                                          stdout='STDOUT_SECRET partial'), critique=Critique(False, 'CRITIC_SECRET')),
    entry(4, '隣接する区対を全件', failure=failure('Generated Python execution failed', 'OutputTooLong: 出力が 9198 bytes で、上限 8192 bytes を超えた。',
                                              stdout='[{"OBSERVATION_SECRET": 1}')),
    entry(5, '駅の一覧', failure=failure('Generated Python output breaks the output contract',
                                      'DuplicateRows: 23 行のうち 16 行が、ほかの行と同じ（重複）。', stdout='[STDOUT_SECRET]')),
    entry(6, '区の代表点', failure=ExecutionFailure('Generated Python execution timed out', '',
                                                'TimeoutError: the sandbox stopped the code after 60 s', None)),
    entry(7, '区の人口', failure=ExecutionFailure('ValueError: Candidate breaks the code contract: input rows: area_ids[0]', '',
                                              'ValueError: Candidate breaks the code contract: input rows: area_ids[0]', None)),
    FinalCriticFailure('FINAL_SECRET 答えが無い', 7),
)


def test_only_the_failures_checked_without_a_model_are_kept():
    kept = checked_failures(EVENTS)
    assert [(failure.step, failure.kind) for failure in kept] == [
        (2, 'planner_contract'), (3, 'execution_error'), (4, 'output_too_long'), (5, 'duplicate_rows'),
        (6, 'timeout'), (7, 'code_contract')]
    assert kept[1].line == "KeyError: 'name'" and kept[1].intent == '歩道を数える' and kept[1].resources == ('overpass',)


def test_a_checked_failure_has_no_field_for_a_judgement_or_a_value():
    assert [field.name for field in dataclasses.fields(CheckedFailure)] == ['step', 'intent', 'resources', 'kind', 'line']


def result(events, stop='max_steps'):
    history = tuple(event for event in events if isinstance(event, HistoryEntry))
    return AdaptiveGoalExecution('G', history, (), stop, Critique(False, 'FINAL_SECRET'), None, tuple(events))


def test_neither_the_record_nor_the_memory_carries_a_judgement_an_observation_or_a_reply(tmp_path):
    graph = ExplorationGraph(tmp_path / 'exploration.jsonl')
    graph.record(1, result(EVENTS), success=False, explored_at='t', elapsed=1.0)
    stored = (tmp_path / 'exploration.jsonl').read_text()
    memory = graph.memory('G')
    for secret in SECRETS:
        assert secret not in json.dumps(json.loads(stored)['checked_failures'], ensure_ascii=False), secret
        assert secret not in memory, secret
    assert "KeyError: 'name'" in memory and 'OutputTooLong' in memory and 'DuplicateRows' in memory
    assert 'max_steps' not in memory                                             # how it stopped can come from a Critic
    assert 'reason' not in json.loads(stored)                                    # no Critic's reason is kept at all


def test_a_hand_edited_record_can_not_slip_a_judgement_in(tmp_path):
    path = tmp_path / 'exploration.jsonl'
    row = {'number': 1, 'goal': 'G', 'success': False, 'checked_failures': [
        {'step': 1, 'intent': 'x', 'resources': [], 'kind': 'execution_error', 'line': 'KeyError: a',
         'critic_reason': 'CRITIC_SECRET', 'observation': 'OBSERVATION_SECRET'}]}
    path.write_text(json.dumps(row) + '\n')
    memory = ExplorationGraph(path).memory('G')
    assert 'KeyError: a' in memory and 'CRITIC_SECRET' not in memory and 'OBSERVATION_SECRET' not in memory


def test_a_goal_whose_last_try_was_answered_or_failed_only_by_judgement_has_no_memory(tmp_path):
    graph = ExplorationGraph(tmp_path / 'exploration.jsonl')
    graph.record(1, result(EVENTS[:2]), success=False, explored_at='t', elapsed=1.0)  # the Critic rejected, nothing ran wrong
    assert graph.memory('G') is None
    graph.record(2, result(EVENTS), success=False, explored_at='t', elapsed=1.0)
    assert graph.memory('G') is not None
    graph.record(3, result(EVENTS[:1], stop='done'), success=True, explored_at='t', elapsed=1.0)
    assert graph.memory('G') is None and graph.memories() == {}


def test_a_goal_that_broke_is_recorded_with_its_error_and_no_failures(tmp_path):
    graph = ExplorationGraph(tmp_path / 'exploration.jsonl')
    row = graph.record(1, None, goal='G', success=False, explored_at='t', elapsed=1.0, error='TimeoutError: timed out')
    assert row['stop_reason'] == 'error' and row['checked_failures'] == [] and graph.memory('G') is None


def test_the_memory_is_bounded_and_keeps_the_latest():
    many = tuple(entry(n, f'手 {n}', failure=failure('failed', 'KeyError: ' + 'k' * 200)) for n in range(1, 60))
    text = ExplorationGraph.render(checked_failures(many))
    assert len(text) <= 2500 and '手 59' in text and '手 1「' not in text


def test_the_planner_is_shown_the_memory_only_when_given_one():
    client = Mock(); client.generate.return_value = 'DONE'
    Planner(client).next('G', GoalHistory())
    assert '前回この Goal を試したとき' not in client.generate.call_args.args[0]
    Planner(client).next('G', GoalHistory(), memory='前回の記録の本文')
    prompt = client.generate.call_args.args[0]
    assert '前回この Goal を試したときに、モデルを使わずに確かめた失敗' in prompt and '前回の記録の本文' in prompt


def test_the_executor_passes_the_memory_to_every_call_of_the_planner():
    from geo_voyager.goal_executor import GoalExecutor
    from geo_voyager.planner import DONE
    planner = Mock(); planner.next.return_value = DONE
    critic = Mock(); critic.check.return_value = Critique(True, 'ok')
    GoalExecutor(planner, Mock(), critic).execute_adaptive('G', memory='M')
    assert planner.next.call_args.kwargs['memory'] == 'M'


def test_the_outcome_shown_to_the_curriculum_is_made_from_checked_failures_only(tmp_path):
    graph = ExplorationGraph(tmp_path / 'exploration.jsonl')
    graph.record(1, result(EVENTS, stop='final_critic_failed'), success=False, explored_at='t', elapsed=1.0)
    graph.record(2, result(EVENTS[:2]), success=False, explored_at='t', elapsed=1.0)
    graph.record(3, None, goal='H', success=False, explored_at='t', elapsed=1.0, error='TimeoutError: CRITIC_SECRET')
    graph.record(4, result(EVENTS[:1], stop='done'), success=True, explored_at='t', elapsed=1.0)
    failed, judged, broke, answered = (outcome(attempt) for attempt in graph.attempts())
    for text in (failed, judged, broke, answered):
        for secret in SECRETS:
            assert secret not in text, secret
        assert 'final_critic_failed' not in text and 'max_steps' not in text
    assert failed.startswith('未達') and 'overpass で実行のエラー' in failed and 'Planner の応答が検査で拒まれた' in failed
    assert judged == '未達' and broke == '未達' and answered == '答えが出た'


def test_the_outcome_is_bounded_and_ignores_fields_added_by_hand():
    many = [{'step': n, 'intent': 'x', 'resources': [f'service-{n}'], 'kind': 'execution_error', 'line': 'KeyError: a',
             'critic_reason': 'CRITIC_SECRET'} for n in range(40)]
    text = outcome({'goal': 'G', 'success': False, 'reason': 'CRITIC_SECRET', 'checked_failures': many})
    assert len(text) <= 160 and 'CRITIC_SECRET' not in text and 'service-39' in text
    assert outcome({'goal': 'G', 'success': False, 'reason': 'CRITIC_SECRET'}) == '未達'   # a record from before ADR 0011
