from uuid import uuid4

import pytest

from geo_voyager.target_ref import TargetRef
from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_history import GoalHistory, HistoryEntry, intent_key
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation


def intent(text='渋谷区の件数', **kwargs):
    return Intent(text, service_ids=('overpass',), **kwargs)


def entry(step=1, obs='{"name": "渋谷区", "relation_id": "1"}', ok=True, **kwargs):
    base = dict(step=step, intent=intent(), observations=(Observation(obs),) if obs else (),
                critique=Critique(ok, 'r'), failure=None, reused_skill_id=None, learned_skill_id=None, targets=())
    base.update(kwargs)
    return HistoryEntry(**base)


def test_the_history_is_append_only_and_entries_are_immutable():
    history = GoalHistory()
    first = entry(1)
    history.append(first)
    assert history.entries == (first,)
    assert isinstance(history.entries, tuple)
    with pytest.raises(AttributeError):
        history.entries.append(entry(2))
    with pytest.raises(Exception):
        first.step = 9
    snapshot = history.entries
    history.append(entry(2))
    assert snapshot == (first,) and len(history) == 2          # a view taken earlier does not change


def test_steps_must_be_numbered_in_order():
    history = GoalHistory()
    with pytest.raises(ValueError):
        history.append(entry(2))
    history.append(entry(1))
    with pytest.raises(ValueError):
        history.append(entry(1))


def test_only_the_observations_of_successful_steps_are_carried_forward():
    history = GoalHistory()
    history.append(entry(1, obs='{"a": 1}'))
    history.append(entry(2, obs='{"b": 2}', ok=False))
    history.append(entry(3, obs='{"c": 3}', failure=ExecutionFailure('f', '', 'KeyError: 0', 73), critique=Critique(False, 'f')))
    history.append(entry(4, obs='{"d": 4}'))
    assert [o.text for o in history.observations()] == ['{"a": 1}', '{"d": 4}']


def test_a_step_succeeds_only_without_failure_and_with_a_passing_critique():
    assert entry(ok=True).succeeded
    assert not entry(ok=False).succeeded
    assert not entry(failure=ExecutionFailure('f', '', 'e', 73), critique=Critique(True, 'x')).succeeded
    assert not entry(critique=None).succeeded


def test_targets_found_in_successful_steps_accumulate_without_repeats():
    history = GoalHistory()
    history.append(entry(1, targets=(TargetRef('渋谷区', 'relation_id', '1'),)))
    history.append(entry(2, ok=False, targets=(TargetRef('港区', 'relation_id', '2'),)))
    history.append(entry(3, targets=(TargetRef('渋谷区', 'relation_id', '1'), TargetRef('新宿区', 'relation_id', '3'))))
    assert history.targets() == (TargetRef('渋谷区', 'relation_id', '1'), TargetRef('新宿区', 'relation_id', '3'))


def test_an_entry_is_built_from_an_intent_execution_with_the_targets_that_are_new():
    history = GoalHistory()
    first = IntentExecution([Observation('{"name": "渋谷区", "relation_id": "1"}')], (), None, None, Critique(True, 'ok'), None)
    history.append(HistoryEntry.from_execution(1, intent(), first, history))
    learned, reused = uuid4(), uuid4()
    second = IntentExecution([Observation('{"name": "渋谷区", "relation_id": "1", "count": 5}'),
                              Observation('{"name": "港区", "relation_id": "2"}')],
                             (), reused, learned, Critique(True, 'ok'), Critique(True, 'skill ok'))
    built = HistoryEntry.from_execution(2, intent('港区の件数'), second, history)
    assert built.targets == (TargetRef('港区', 'relation_id', '2'),)        # 渋谷区 was already known
    assert built.reused_skill_id == reused and built.learned_skill_id == learned


def test_a_skill_that_failed_the_critic_is_not_counted_as_reused():
    execution = IntentExecution([Observation('{"x": 1}')], (), uuid4(), None, Critique(True, 'ok'), Critique(False, 'skill failed'))
    assert HistoryEntry.from_execution(1, intent(), execution, GoalHistory()).reused_skill_id is None


def test_a_failed_execution_keeps_its_failure_and_discovers_no_targets():
    failure = ExecutionFailure('failed', '', 'KeyError: 0', 73)
    execution = IntentExecution([], (), None, None, Critique(False, 'failed'), None, failure=failure)
    built = HistoryEntry.from_execution(1, intent(), execution, GoalHistory())
    assert built.failure == failure and built.targets == () and not built.succeeded


def test_the_intent_key_ignores_whitespace_but_not_the_target_or_resources():
    assert intent_key(intent('渋谷区  の件数')) == intent_key(intent('渋谷区 の件数'))
    assert intent_key(intent(target=TargetRef('渋谷区'))) != intent_key(intent(target=TargetRef('港区')))
    assert intent_key(Intent('x', service_ids=('overpass',))) != intent_key(Intent('x', service_ids=('nominatim',)))


def test_entries_for_the_same_intent_are_found_by_key():
    history = GoalHistory()
    history.append(entry(1))
    history.append(entry(2, intent=intent('別の件数')))
    history.append(entry(3, ok=False))
    assert [e.step for e in history.entries_for(intent())] == [1, 3]


from geo_voyager.goal_history import FinalCriticFailure, PlannerFailure


def test_failures_are_recorded_in_the_history_in_order_with_the_steps():
    history = GoalHistory()
    history.append(entry(1))
    history.append(PlannerFailure('ValueError: more than one 対象 line', reply='調査項目: x\n対象: a\n対象: b', after_step=1))
    history.append(entry(2))
    history.append(FinalCriticFailure('件数が足りない', after_step=2))
    kinds = [type(event).__name__ for event in history.events]
    assert kinds == ['HistoryEntry', 'PlannerFailure', 'HistoryEntry', 'FinalCriticFailure']


def test_failures_are_not_steps_and_do_not_change_the_step_numbering_or_observations():
    history = GoalHistory()
    history.append(PlannerFailure('bad plan', after_step=0))
    assert len(history) == 0 and history.entries == () and history.observations() == ()
    history.append(entry(1, obs='{"a": 1}'))              # the first step is still step 1
    history.append(FinalCriticFailure('not yet', after_step=1))
    assert len(history) == 1 and [o.text for o in history.observations()] == ['{"a": 1}']


def test_the_two_kinds_of_failure_can_be_listed_separately():
    history = GoalHistory()
    first, second = PlannerFailure('one'), PlannerFailure('two')
    critic = FinalCriticFailure('three')
    for event in (first, entry(1), second, critic):
        history.append(event)
    assert history.planner_failures() == (first, second) and history.final_critic_failures() == (critic,)


def test_events_are_immutable_and_the_view_does_not_change_later():
    history = GoalHistory()
    history.append(PlannerFailure('one'))
    snapshot = history.events
    history.append(FinalCriticFailure('two'))
    assert len(snapshot) == 1 and len(history.events) == 2
    with pytest.raises(Exception):
        snapshot[0].reason = 'changed'


def test_an_unknown_kind_of_event_is_refused():
    with pytest.raises(TypeError):
        GoalHistory().append('not an event')
