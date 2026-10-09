from unittest.mock import Mock
from uuid import uuid4

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation
from geo_voyager.planner import DONE


def intent(text, **kwargs):
    return Intent(text, service_ids=('overpass',), **kwargs)


def ok(*texts, learned=None, reused=None):
    return IntentExecution([Observation(t) for t in texts], (), reused, learned, Critique(True, 'ok'),
                           Critique(True, 'skill ok') if reused else None)


def critic_rejected(*texts):
    return IntentExecution([Observation(t) for t in texts], (), None, None, Critique(False, '足りない'), None)


def crashed():
    failure = ExecutionFailure('failed', '', 'KeyError: 0', 73)
    return IntentExecution([], (), None, None, Critique(False, 'Generated Python execution failed'), None, failure=failure)


class Script:
    """A Planner that returns scripted decisions and records what it was shown."""

    def __init__(self, *decisions):
        self.decisions, self.seen = list(decisions), []

    def next(self, goal, history):
        self.seen.append((goal, history.entries, history.targets(), [o.text for o in history.observations()]))
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


def run(planner, executions, critic=None, **kwargs):
    executor = Mock(); executor.execute.side_effect = executions
    if critic is None:
        critic = Mock(); critic.check.return_value = Critique(True, 'goal answered')
    return GoalExecutor(planner, executor, critic).execute_adaptive('目標', **kwargs), executor, critic


def test_the_planner_is_asked_after_every_step_with_a_growing_append_only_history():
    planner = Script(intent('a'), intent('b'), DONE)
    result, _, _ = run(planner, [ok('1'), ok('2')])
    assert [len(entries) for _, entries, _, _ in planner.seen] == [0, 1, 2]
    first_view = planner.seen[1][1]
    assert planner.seen[2][1][:1] == first_view                       # earlier entries are unchanged
    assert result.stop_reason == 'done' and [e.step for e in result.history] == [1, 2]


def test_the_full_plan_is_never_used_on_this_route():
    planner = Mock(spec=['next']); planner.next.side_effect = [intent('a'), DONE]
    result, _, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'done'


def test_done_ends_the_goal_with_a_final_check_of_everything_that_succeeded():
    result, executor, critic = run(Script(intent('a'), intent('b'), DONE), [ok('1'), crashed()])
    assert result.stop_reason == 'done' and result.critique == Critique(True, 'goal answered')
    final_intent, observations = critic.check.call_args.args
    assert final_intent.text == '目標' and [o.text for o in observations] == ['1']      # the crashed step adds nothing


def test_a_step_receives_only_the_observations_of_the_steps_that_succeeded():
    planner = Script(intent('a'), intent('b'), intent('c'), DONE)
    _, executor, _ = run(planner, [ok('1'), critic_rejected('wrong'), ok('3')])
    received = [[o.text for o in call.args[0].previous_observations] for call in executor.execute.call_args_list]
    assert received == [[], ['1'], ['1']]


def test_a_failure_does_not_end_the_goal_and_the_planner_sees_it_before_replanning():
    planner = Script(intent('a'), intent('a but another way'), DONE)
    result, _, _ = run(planner, [crashed(), ok('answer')])
    after_failure = planner.seen[1][1]
    assert after_failure[0].failure is not None and not after_failure[0].succeeded
    assert [e.succeeded for e in result.history] == [False, True] and result.stop_reason == 'done'


def test_a_target_first_made_known_by_a_step_is_known_to_the_planner_at_the_next_step():
    planner = Script(intent('港区の ID'), intent('港区の件数', target_name='港区'), DONE)
    run(planner, [ok('{"name": "港区", "relation_id": "1761717"}'), ok('{"name": "港区", "relation_id": "1761717", "count": 22}')])
    assert planner.seen[0][2] == () and planner.seen[1][2] == ({'name': '港区', 'relation_id': '1761717'},)
    assert planner.seen[2][2] == ({'name': '港区', 'relation_id': '1761717'},)         # not added twice


def test_the_history_keeps_which_skill_was_learned_and_which_was_reused():
    learned, reused = uuid4(), uuid4()
    planner = Script(intent('a'), intent('a again'), DONE)
    result, _, _ = run(planner, [ok('1', learned=learned), ok('2', reused=reused)])
    assert result.history[0].learned_skill_id == learned and result.history[0].reused_skill_id is None
    assert result.history[1].reused_skill_id == reused


def test_the_goal_stops_at_the_step_limit():
    planner = Script(*[intent(f'step {n}') for n in range(10)])
    result, executor, critic = run(planner, [ok(str(n)) for n in range(10)], max_steps=3)
    assert result.stop_reason == 'max_steps' and executor.execute.call_count == 3 and len(result.history) == 3
    assert not result.critique.success and 'max_steps' in result.critique.reason
    critic.check.assert_not_called()


def test_an_intent_that_already_succeeded_is_not_run_again():
    planner = Script(intent('a'), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'repeated_intent' and executor.execute.call_count == 1
    assert not result.critique.success


def test_the_same_whitespace_variant_counts_as_a_repeat():
    result, executor, _ = run(Script(intent('a  b'), intent('a b')), [ok('1')])
    assert result.stop_reason == 'repeated_intent' and executor.execute.call_count == 1


def test_a_failed_intent_may_be_tried_once_more_and_then_the_goal_stops():
    planner = Script(intent('a'), intent('a'), intent('a'), DONE)
    result, executor, _ = run(planner, [crashed(), crashed()])
    assert result.stop_reason == 'repeated_intent' and executor.execute.call_count == 2


def test_a_different_target_is_a_different_intent():
    planner = Script(intent('件数', target_name='港区'), intent('件数', target_name='新宿区'), DONE)
    result, executor, _ = run(planner, [ok('1'), ok('2')])
    assert result.stop_reason == 'done' and executor.execute.call_count == 2


def test_a_plan_the_planner_can_not_produce_ends_the_goal_with_the_reason():
    planner = Script(intent('a'), ValueError('Plan must start with 調査項目:'))
    result, _, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'planner_error' and 'Plan must start' in result.critique.reason
    assert len(result.history) == 1


def test_a_step_the_executor_refuses_ends_the_goal_as_a_plan_error():
    executor = Mock(); executor.execute.side_effect = ValueError('At most one dataset_id')
    result = GoalExecutor(Script(intent('a')), executor, Mock()).execute_adaptive('目標')
    assert result.stop_reason == 'planner_error' and len(result.history) == 0


def test_done_before_any_step_succeeded_fails_the_goal_through_the_critic():
    critic = Mock(); critic.check.return_value = Critique(False, 'Observation がありません')
    result, _, _ = run(Script(DONE), [], critic=critic)
    assert result.stop_reason == 'done' and not result.critique.success
    assert critic.check.call_args.args[1] == ()


def test_the_executions_are_kept_for_provenance():
    executions = [ok('1'), crashed()]
    result, _, _ = run(Script(intent('a'), intent('b'), DONE), executions)
    assert result.executions == tuple(executions)
