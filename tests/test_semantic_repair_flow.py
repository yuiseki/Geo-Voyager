from unittest.mock import Mock, patch

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.semantic_repairer import SemanticRepair
from geo_voyager.skill_candidate import SkillCandidate

FAILURE = ExecutionFailure('failed', '', 'KeyError: 0', 73)
FIRST = SkillCandidate('first', '説明')
FIXED = SkillCandidate('fixed', '修正後')
REASON = '件数が0で足りない'


def build(critiques, runs, semantic=None, with_semantic=True):
    retriever, selector, worker, generator, critic, library, repairer = [Mock() for _ in range(7)]
    retriever.retrieve.return_value = []; selector.select.return_value = None
    generator.generate.return_value = FIRST
    worker.execute_candidate.side_effect = runs
    critic.check.side_effect = critiques
    semantic_repairer = Mock()
    semantic_repairer.repair.return_value = semantic if semantic is not None else SemanticRepair(FIXED, 'proposed')
    executor = IntentExecutor(retriever, selector, worker, generator, critic, library, repairer,
                              semantic_repairer=semantic_repairer if with_semantic else None)
    return executor, semantic_repairer, worker, critic, library, repairer


def run(executor):
    with patch('geo_voyager.intent_executor.promote') as promote:
        promote.side_effect = lambda candidate: Mock(id=candidate.code)
        return executor.execute(Intent('港区の件数', service_ids=('overpass',))), promote


def test_it_does_not_fire_when_the_critic_passes():
    executor, semantic, _, critic, _, _ = build([Critique(True, 'ok')], [[Observation('a')]])
    result, _ = run(executor)
    assert result.critique.success and semantic.repair.call_count == 0 and critic.check.call_count == 1


def test_it_does_not_fire_when_the_execution_failed():
    executor, semantic, _, critic, _, repairer = build([], [FAILURE, FAILURE, FAILURE])
    repairer.repair.return_value = FIRST
    result, _ = run(executor)
    assert not result.critique.success and semantic.repair.call_count == 0 and critic.check.call_count == 0


def test_a_rescued_intent_runs_the_repaired_code_and_asks_the_critic_again():
    executor, semantic, worker, critic, library, repairer = build(
        [Critique(False, REASON), Critique(True, 'now ok')], [[Observation('{"count": 0}')], [Observation('{"count": 7}')]])
    result, promote = run(executor)
    assert result.critique.success and result.critique.reason == 'now ok'
    assert [o.text for o in result.observations] == ['{"count": 7}']
    assert worker.execute_candidate.call_args_list[1].args[1] == FIXED
    assert critic.check.call_count == 2
    promote.assert_called_once_with(FIXED)           # only the repaired candidate is saved
    assert library.add.call_count == 1 and repairer.repair.call_count == 0


def test_it_passes_what_the_repair_needs_and_only_once():
    executor, semantic, *_ = build([Critique(False, REASON), Critique(False, 'still')],
                                   [[Observation('{"count": 0}')], [Observation('{"count": 0}')]])
    run(executor)
    assert semantic.repair.call_count == 1
    intent, candidate, observations, reason = semantic.repair.call_args.args
    assert candidate == FIRST and [o.text for o in observations] == ['{"count": 0}'] and reason == REASON
    assert [a.code for a in semantic.repair.call_args.kwargs['history']] == ['first']


def test_a_repair_the_critic_still_rejects_leaves_the_original_result_and_saves_nothing():
    executor, _, worker, critic, library, _ = build([Critique(False, REASON), Critique(False, 'still wrong')],
                                                    [[Observation('{"count": 0}')], [Observation('{"count": 9}')]])
    result, promote = run(executor)
    assert not result.critique.success and result.critique.reason == REASON
    assert [o.text for o in result.observations] == ['{"count": 0}']
    assert worker.execute_candidate.call_count == 2 and critic.check.call_count == 2
    promote.assert_not_called(); library.add.assert_not_called()


def test_a_repair_that_does_not_run_keeps_the_original_result_and_does_not_use_the_runtime_route():
    executor, _, worker, critic, library, repairer = build([Critique(False, REASON)],
                                                           [[Observation('{"count": 0}')], FAILURE])
    result, promote = run(executor)
    assert not result.critique.success and [o.text for o in result.observations] == ['{"count": 0}']
    assert result.failure is None                      # the failed semantic run is not the Intent's failure
    assert repairer.repair.call_count == 0 and critic.check.call_count == 1
    promote.assert_not_called()


def test_an_unchanged_or_rejected_proposal_is_not_run():
    for status in ('unchanged', 'vibration', 'hardcoded', 'invalid'):
        executor, _, worker, critic, _, _ = build([Critique(False, REASON)], [[Observation('{"count": 0}')]],
                                                  semantic=SemanticRepair(FIXED if status != 'invalid' else None, status))
        result, _ = run(executor)
        assert worker.execute_candidate.call_count == 1 and critic.check.call_count == 1
        attempt = [a for a in result.attempts if a.route == 'semantic'][0]
        assert attempt.executed is False and attempt.note == status


def test_provenance_keeps_the_runtime_attempts_the_critic_verdicts_and_the_semantic_attempt():
    executor, *_ = build([Critique(False, REASON), Critique(True, 'now ok')],
                         [[Observation('{"count": 0}')], [Observation('{"count": 7}')]])
    result, _ = run(executor)
    runtime, semantic = result.attempts[0], result.attempts[1]
    assert runtime.route == 'runtime' and runtime.critique == Critique(False, REASON)
    assert semantic.route == 'semantic' and semantic.code == 'fixed' and semantic.trigger == REASON
    assert semantic.critique == Critique(True, 'now ok') and semantic.executed and semantic.failure is None
    assert len(result.attempts) == 2


def test_without_a_semantic_repairer_nothing_changes():
    executor, semantic, worker, critic, *_ = build([Critique(False, REASON)], [[Observation('a')]], with_semantic=False)
    result, _ = run(executor)
    assert not result.critique.success and worker.execute_candidate.call_count == 1
    assert [a.route for a in result.attempts] == ['runtime']


def test_a_runtime_repair_comes_first_and_the_semantic_repair_follows_a_successful_run():
    executor, semantic, worker, critic, _, repairer = build(
        [Critique(False, REASON), Critique(True, 'ok')], [FAILURE, [Observation('{"count": 0}')], [Observation('{"count": 5}')]])
    repairer.repair.return_value = SkillCandidate('runtime-fixed', '修正')
    result, _ = run(executor)
    assert [a.route for a in result.attempts] == ['runtime', 'runtime', 'semantic']
    assert semantic.repair.call_args.args[1].code == 'runtime-fixed'
    assert [a.code for a in semantic.repair.call_args.kwargs['history']] == ['first', 'runtime-fixed']
