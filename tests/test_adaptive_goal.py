from unittest.mock import Mock

from geo_voyager.target_ref import TargetRef
from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation
from geo_voyager.goal_history import FinalCriticFailure, PlannerFailure
from geo_voyager.planner import DONE, PlannerRejected


def intent(text, **kwargs):
    return Intent(text, service_ids=('overpass',), **kwargs)


def ok(*texts, learned=None, reused=()):
    return IntentExecution([Observation(t) for t in texts], (), reused, learned, Critique(True, 'ok'))


def critic_rejected(*texts):
    return IntentExecution([Observation(t) for t in texts], (), (), None, Critique(False, '足りない'))


def crashed():
    failure = ExecutionFailure('failed', '', 'KeyError: 0', 73)
    return IntentExecution([], (), (), None, Critique(False, 'Generated Python execution failed'), failure=failure)


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


def test_a_step_receives_the_results_it_names_in_the_order_it_names_them():
    minato = '{"name": "港区", "count": 46}'
    wards = '[{"name": "世田谷区", "count": 40}, {"name": "港区", "count": 46}]'
    planner = Script(intent('港区の駅', result_name='minato_stations'), intent('各区の駅', result_name='ward_stations'),
                     intent('人口', result_name='ward_population'),
                     Intent('人口あたりの駅', requires_context=True, result_name='ratio',
                            inputs=('ward_population', 'ward_stations')), DONE)
    _, executor, critic = run(planner, [ok(minato), ok(wards), ok('[1]'), ok('86')])
    received = [[o.text for o in call.args[0].previous_observations] for call in executor.execute.call_args_list]
    assert received[3] == ['[1]', wards]                         # not the trial on Minato
    given = executor.execute.call_args_list[3].args[0]
    assert given.inputs == ('ward_population', 'ward_stations')
    assert given.input_notes == ('step 3「人口」（overpass）', 'step 2「各区の駅」（overpass）')


def test_a_step_that_names_no_inputs_receives_nothing():
    planner = Script(intent('a', result_name='a'), intent('b', result_name='b', inputs=()), DONE)
    _, executor, _ = run(planner, [ok('1'), ok('2')])
    assert executor.execute.call_args_list[1].args[0].previous_observations == ()


def test_a_failure_does_not_end_the_goal_and_the_planner_sees_it_before_replanning():
    planner = Script(intent('a'), intent('a but another way'), DONE)
    result, _, _ = run(planner, [crashed(), ok('answer')])
    after_failure = planner.seen[1][1]
    assert after_failure[0].failure is not None and not after_failure[0].succeeded
    assert [e.succeeded for e in result.history] == [False, True] and result.stop_reason == 'done'


def test_a_target_first_made_known_by_a_step_is_known_to_the_planner_at_the_next_step():
    planner = Script(intent('港区の ID'), intent('港区の件数', target=TargetRef('港区')), DONE)
    run(planner, [ok('{"name": "港区", "relation_id": "1761717"}'), ok('{"name": "港区", "relation_id": "1761717", "count": 22}')])
    assert planner.seen[0][2] == () and planner.seen[1][2] == (TargetRef('港区', 'relation_id', '1761717'),)
    assert planner.seen[2][2] == (TargetRef('港区', 'relation_id', '1761717'),)         # not added twice


def test_the_history_keeps_which_skill_was_learned_and_which_was_called():
    learned, reused = 'count_tag_in_area@v1', ('count_tag_in_area@v1',)
    planner = Script(intent('a'), intent('a again'), DONE)
    result, _, _ = run(planner, [ok('1', learned=learned), ok('2', reused=reused)])
    assert result.history[0].learned_skill == learned and result.history[0].called_skills == ()
    assert result.history[1].called_skills == reused


def test_the_goal_stops_at_the_step_limit():
    planner = Script(*[intent(f'step {n}') for n in range(10)])
    result, executor, critic = run(planner, [ok(str(n)) for n in range(10)], max_steps=3)
    assert result.stop_reason == 'max_steps' and executor.execute.call_count == 3 and len(result.history) == 3
    assert not result.critique.success and 'max_steps' in result.critique.reason
    critic.check.assert_not_called()
    assert len(planner.seen) == 4                         # asked once more after the last step, and it was not DONE


def test_the_planner_can_still_say_done_after_the_last_step():
    # Replay of round 3: the eighth step printed the answer and the Goal ended as max_steps before DONE could be said.
    planner = Script(intent('a'), intent('b'), DONE)
    result, executor, critic = run(planner, [ok('1'), ok('2')], max_steps=2)
    assert result.stop_reason == 'done' and executor.execute.call_count == 2


class Clock:
    """A clock that moves on by the given seconds each time it is read."""

    def __init__(self, *readings):
        self.readings = list(readings)

    def __call__(self):
        return self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]


def test_the_goal_stops_at_the_time_limit_and_the_planner_may_still_say_done():
    # Exploration 13 (2026-10-17): the 6 Goals that ran out of steps took 58 minutes each, 38% of the 15.2 hours.
    planner = Script(intent('a'), intent('b'), intent('c'))
    result, executor, critic = run(planner, [ok('1'), ok('2'), ok('3')], time_limit=1800, clock=Clock(0, 0, 900, 1900))
    assert result.stop_reason == 'time_limit' and executor.execute.call_count == 2
    assert not result.critique.success and 'time_limit' in result.critique.reason
    assert len(planner.seen) == 3                         # asked once more when the time was up, and it was not DONE
    planner = Script(intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')], time_limit=1800, clock=Clock(0, 0, 1900))
    assert result.stop_reason == 'done' and executor.execute.call_count == 1


def test_without_a_time_limit_the_clock_is_not_a_limit():
    planner = Script(intent('a'), intent('b'), DONE)
    result, _, _ = run(planner, [ok('1'), ok('2')], clock=Clock(0, 10 ** 9))
    assert result.stop_reason == 'done'


def test_after_the_last_step_a_final_critic_failure_or_a_rejected_reply_ends_the_goal():
    for decision in (DONE, PlannerRejected('ValueError: x', 'reply')):
        critic = Mock(); critic.check.return_value = Critique(False, 'not answered')
        planner = Script(intent('a'), decision, DONE)
        result, executor, _ = run(planner, [ok('1')], critic, max_steps=1)
        assert result.stop_reason == 'max_steps' and executor.execute.call_count == 1 and len(planner.seen) == 2


# GeoAI-master-skills' small tasks (2026-10-15): a repeat ended tasks 17 and 11, after the Planner had named the pitfall
# (Natural Earth's ISO_A3_EH shared by a country and its dependencies) and the code broke on quoting a name. A repeat
# is now sent back to the Planner as a Planner failure, which it can answer by splitting the step or changing it.

def test_an_intent_that_already_succeeded_is_not_run_again_and_the_planner_is_told():
    planner = Script(intent('a'), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')])
    assert executor.execute.call_count == 1 and len(planner.seen) == 3
    failures = [event for event in result.events if isinstance(event, PlannerFailure)]
    assert len(failures) == 1 and '既に成功している' in failures[0].reason


def test_the_same_whitespace_variant_counts_as_a_repeat():
    result, executor, _ = run(Script(intent('a  b'), intent('a b'), DONE), [ok('1')])
    assert executor.execute.call_count == 1
    assert any(isinstance(event, PlannerFailure) for event in result.events)


def test_a_failed_intent_may_be_tried_once_more_and_then_is_sent_back_to_the_planner():
    planner = Script(intent('a'), intent('a'), intent('a'), intent('b'), DONE)
    result, executor, _ = run(planner, [crashed(), crashed(), ok('2')])
    assert executor.execute.call_count == 3                       # a, a, then b
    failures = [event for event in result.events if isinstance(event, PlannerFailure)]
    assert len(failures) == 1 and '2 回失敗した' in failures[0].reason


def test_a_planner_that_keeps_repeating_stops_as_a_planner_failure():
    planner = Script(intent('a'), intent('a'), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'planner_failure' and executor.execute.call_count == 1


def test_a_different_target_is_a_different_intent():
    planner = Script(intent('件数', target=TargetRef('港区')), intent('件数', target=TargetRef('新宿区')), DONE)
    result, executor, _ = run(planner, [ok('1'), ok('2')])
    assert result.stop_reason == 'done' and executor.execute.call_count == 2


def test_a_plan_the_planner_can_not_produce_ends_the_goal_with_the_reason():
    planner = Script(intent('a'), ValueError('Plan must start with 調査項目:'))
    result, _, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'planner_error' and 'Plan must start' in result.critique.reason
    assert len(result.history) == 1


def test_the_executions_are_kept_for_provenance():
    executions = [ok('1'), crashed()]
    result, _, _ = run(Script(intent('a'), intent('b'), DONE), executions)
    assert result.executions == tuple(executions)


def rejected(reason='ValueError: An Intent has more than one 対象 line', reply='調査項目: x\n対象: a\n対象: b'):
    return PlannerRejected(reason, reply)


def planner_failures(result):
    return [event for event in result.events if isinstance(event, PlannerFailure)]


def final_failures(result):
    return [event for event in result.events if isinstance(event, FinalCriticFailure)]


# ---- planner failures

def test_an_unusable_plan_is_recorded_as_a_failure_and_the_goal_plans_again():
    planner = Script(intent('a'), rejected(), intent('a1'), intent('a2'), DONE)
    result, executor, _ = run(planner, [ok('1'), ok('2'), ok('3')])
    [failure] = planner_failures(result)
    assert failure.reason.startswith('ValueError: An Intent has more than one') and failure.reply == '調査項目: x\n対象: a\n対象: b'
    assert failure.after_step == 1
    assert result.stop_reason == 'done' and len(result.history) == 3 and executor.execute.call_count == 3


def test_the_planner_sees_its_failure_when_it_plans_again():
    planner = Script(rejected(), intent('a'), DONE)
    run(planner, [ok('1')])
    assert planner.seen[0][1] == () and planner.seen[1][1] == ()               # no steps were executed
    # the Script records only steps, so check the failure through the history it was given
    seen = Mock()
    class Watch(Script):
        def next(self, goal, history):
            seen(history.events)
            return super().next(goal, history)
    run(Watch(rejected(), intent('a'), DONE), [ok('1')])
    assert [type(e).__name__ for e in seen.call_args_list[1].args[0]] == ['PlannerFailure']


def test_a_planner_failure_is_not_a_step_and_carries_nothing_forward():
    planner = Script(intent('a'), rejected(), intent('b'), DONE)
    result, executor, _ = run(planner, [ok('1'), ok('2')])
    assert [e.step for e in result.history] == [1, 2]
    received = [[o.text for o in c.args[0].previous_observations] for c in executor.execute.call_args_list]
    assert received == [[], ['1']]


def test_the_same_planner_failure_twice_stops_the_goal():
    planner = Script(rejected(), rejected(), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'planner_failure' and len(planner_failures(result)) == 2
    assert executor.execute.call_count == 0 and not result.critique.success
    assert 'planner_failure' in result.critique.reason and 'more than one' in result.critique.reason


def test_different_planner_failures_are_bounded_too():
    planner = Script(rejected('one'), rejected('two'), rejected('three'), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')], max_planner_failures=3)
    assert result.stop_reason == 'planner_failure' and len(planner_failures(result)) == 3
    assert len(planner.decisions) == 2                                              # it did not keep asking


def test_a_planner_that_never_produces_a_usable_plan_stops_after_a_bounded_number_of_calls():
    class Garbage:
        calls = 0
        def next(self, goal, history):
            Garbage.calls += 1
            raise PlannerRejected(f'ValueError: bad {Garbage.calls}', 'x')
    executor = Mock()
    result = GoalExecutor(Garbage(), executor, Mock()).execute_adaptive('目標', max_planner_failures=3)
    assert result.stop_reason == 'planner_failure' and Garbage.calls == 3


def test_an_error_that_is_not_a_rejected_reply_still_ends_the_goal_at_once():
    planner = Script(ValueError('Goal must not be empty'), intent('a'), DONE)
    result, executor, _ = run(planner, [ok('1')])
    assert result.stop_reason == 'planner_error' and planner_failures(result) == [] and executor.execute.call_count == 0


def test_an_intent_with_two_datasets_is_run():
    # A station is put in its ward by joining the station and the boundary tables in one step.
    two_datasets = Intent('駅を区に入れる', dataset_ids=('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp'))
    result, executor, _ = run(Script(two_datasets, DONE), [ok('1')])
    assert planner_failures(result) == [] and executor.execute.call_count == 1 and result.stop_reason == 'done'


def test_a_local_step_with_nothing_to_work_on_is_a_planner_failure_too():
    local = Intent('前段を集計', requires_context=True)
    executor = Mock(); executor.execute.side_effect = [ok('1')]
    critic = Mock(); critic.check.return_value = Critique(True, 'answered')
    result = GoalExecutor(Script(local, intent('a'), DONE), executor, critic).execute_adaptive('目標')
    assert len(planner_failures(result)) == 1 and executor.execute.call_count == 1


def test_a_format_error_inside_the_executor_is_a_failed_step_not_a_planner_failure():
    executor = Mock(); executor.execute.side_effect = [ValueError('Candidate code must use a Python code fence'), ok('1')]
    critic = Mock(); critic.check.return_value = Critique(True, 'answered')
    planner = Script(intent('a'), intent('a again'), DONE)
    result = GoalExecutor(planner, executor, critic).execute_adaptive('目標')
    assert planner_failures(result) == [] and [e.succeeded for e in result.history] == [False, True]
    failed = result.history[0]
    assert failed.failure is not None and 'code fence' in failed.failure.stderr
    assert not failed.critique.success and failed.observations == ()
    assert result.stop_reason == 'done'


def test_a_step_that_failed_inside_the_executor_is_shown_to_the_planner_as_an_execution_failure():
    from geo_voyager.goal_history import render_history
    executor = Mock(); executor.execute.side_effect = [ValueError('Critique must contain 判定'), ok('1')]
    critic = Mock(); critic.check.return_value = Critique(True, 'answered')
    texts = []
    class Watch(Script):
        def next(self, goal, history):
            texts.append(render_history(history))
            return super().next(goal, history)
    GoalExecutor(Watch(intent('a'), intent('b'), DONE), executor, critic).execute_adaptive('目標')
    assert '実行失敗' in texts[1] and 'Critique must contain' in texts[1] and '計画の失敗' not in texts[1]


# ---- final critic failures

def critic_that_says(*verdicts):
    critic = Mock(); critic.check.side_effect = list(verdicts)
    return critic


def test_done_followed_by_a_critic_failure_goes_back_to_the_planner_with_the_reason():
    seen = []
    class Watch(Script):
        def next(self, goal, history):
            seen.append(history.events)
            return super().next(goal, history)
    planner = Watch(intent('a'), DONE, intent('b'), DONE)
    result, executor, critic = run(planner, [ok('1'), ok('2')],
                                   critic=critic_that_says(Critique(False, '上位3つが足りない'), Critique(True, 'answered')))
    [failure] = final_failures(result)
    assert failure.reason == '上位3つが足りない' and failure.after_step == 1
    assert [type(e).__name__ for e in seen[2]] == ['HistoryEntry', 'FinalCriticFailure']      # the Planner saw it
    assert result.stop_reason == 'done' and result.critique.success and critic.check.call_count == 2
    assert [o.text for o in critic.check.call_args.args[1]] == ['1', '2']                      # the new step counts


def test_an_early_done_with_nothing_done_yet_is_recovered_from():
    result, executor, critic = run(Script(DONE, intent('a'), DONE), [ok('1')],
                                   critic=critic_that_says(Critique(False, 'Observation がありません'), Critique(True, 'ok')))
    assert result.stop_reason == 'done' and len(result.history) == 1 and final_failures(result)[0].after_step == 0


def test_the_same_final_critic_reason_twice_stops_the_goal():
    planner = Script(intent('a'), DONE, DONE, intent('b'))
    result, executor, critic = run(planner, [ok('1')], critic=critic_that_says(Critique(False, '不足'), Critique(False, '不足')))
    assert result.stop_reason == 'final_critic_failed' and len(final_failures(result)) == 2
    assert not result.critique.success and '不足' in result.critique.reason and executor.execute.call_count == 1


def test_final_critic_failures_are_bounded():
    planner = Script(intent('a'), DONE, intent('b'), DONE, intent('c'), DONE, intent('d'))
    result, executor, critic = run(planner, [ok('1'), ok('2'), ok('3')], max_final_critic_failures=3,
                                   critic=critic_that_says(Critique(False, 'r1'), Critique(False, 'r2'), Critique(False, 'r3')))
    assert result.stop_reason == 'final_critic_failed' and len(final_failures(result)) == 3 and len(planner.decisions) == 1


def test_a_planner_that_says_done_forever_is_stopped():
    class AlwaysDone:
        calls = 0
        def next(self, goal, history):
            AlwaysDone.calls += 1
            return DONE
    critic = Mock(); critic.check.return_value = Critique(False, 'まだ')
    result = GoalExecutor(AlwaysDone(), Mock(), critic).execute_adaptive('目標', max_final_critic_failures=3)
    assert result.stop_reason == 'final_critic_failed' and AlwaysDone.calls <= 2        # the repeated reason stops it first


def test_the_loop_is_bounded_whatever_the_mix_of_failures():
    class Mixed:
        calls = 0
        def next(self, goal, history):
            Mixed.calls += 1
            if Mixed.calls % 2:
                raise PlannerRejected(f'ValueError: bad {Mixed.calls}', '')
            return DONE
    critic = Mock(); critic.check.side_effect = [Critique(False, f'r{n}') for n in range(50)]
    result = GoalExecutor(Mixed(), Mock(), critic).execute_adaptive('目標')
    assert result.stop_reason in ('planner_failure', 'final_critic_failed') and Mixed.calls <= 8


# ---- provenance

def test_every_event_is_kept_in_order_in_the_result():
    planner = Script(intent('a'), rejected(), intent('b'), DONE, intent('c'), DONE)
    result, _, _ = run(planner, [ok('1'), ok('2'), ok('3')],
                       critic=critic_that_says(Critique(False, 'もう少し'), Critique(True, 'ok')))
    assert [type(e).__name__ for e in result.events] == [
        'HistoryEntry', 'PlannerFailure', 'HistoryEntry', 'FinalCriticFailure', 'HistoryEntry']
    assert [e.step for e in result.history] == [1, 2, 3]                    # history keeps only the steps


def test_a_goal_that_ended_on_a_failure_still_lists_it():
    result, _, _ = run(Script(rejected(), rejected()), [])
    assert [type(e).__name__ for e in result.events] == ['PlannerFailure', 'PlannerFailure']


def test_the_final_check_is_marked_as_the_final_one():
    _, _, critic = run(Script(intent('a'), DONE), [ok('1')])
    assert critic.check.call_args.kwargs == {'final': True, 'asked': ('step_1: a',)}


def test_the_final_check_is_told_which_succeeded_step_produced_each_observation():
    _, _, critic = run(Script(intent('a'), intent('b'), intent('c'), DONE), [ok('1'), crashed(), ok('3')])
    assert critic.check.call_args.kwargs['asked'] == ('step_1: a', 'step_3: c')


def test_the_final_check_judges_the_latest_result_under_each_name_with_its_name():
    planner = Script(intent('港区の駅', result_name='stations'), intent('各区の駅', result_name='stations'),
                     intent('最多', result_name='most'), DONE)
    _, _, critic = run(planner, [ok('{"count": 46}'), ok('[40, 46]'), ok('{"name": "千代田区"}')])
    _, observations = critic.check.call_args.args
    assert [o.text for o in observations] == ['[40, 46]', '{"name": "千代田区"}']
    assert critic.check.call_args.kwargs['asked'] == ('stations: 各区の駅', 'most: 最多')
