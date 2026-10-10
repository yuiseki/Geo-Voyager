"""IntentExecutor with Skills as named functions (as MineDojo/Voyager): retrieve the closest Skills, generate code
that may call them, run it with them linked in front, repair a failure, judge it, and save the new function."""
from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_library import SkillLibrary

FAILURE = ExecutionFailure('failed', '', 'Traceback\nKeyError: x', 73)
COUNT = ('def count_tag_in_area(key, value, relation_id):\n    """Count the features with a tag in an area."""\n'
         '    return 3\n')
NEW = COUNT + '\n\nprint(count_tag_in_area("amenity", "cafe", intent_target["id_value"]))'
CALLS = 'print(count_tag_in_area("amenity", "hospital", intent_target["id_value"]))'
INTENT = Intent('渋谷区の cafe を数える', service_ids=('overpass',))


def executor(tmp_path, candidates, results, critiques=(Critique(True, 'answered'),), retrieved=()):
    library = SkillLibrary(tmp_path / 'skills')
    retriever, worker, generator, critic, repairer = Mock(), Mock(), Mock(), Mock(), Mock()
    retriever.retrieve.return_value = list(retrieved)
    generator.generate.return_value = candidates[0]
    repairer.repair.side_effect = list(candidates[1:])
    worker.execute_candidate.side_effect = list(results)
    critic.check.side_effect = list(critiques)
    return IntentExecutor(retriever, worker, generator, critic, library, repairer), library, (retriever, worker, generator, critic, repairer)


def test_a_new_function_is_saved_as_a_skill_when_the_critic_accepts(tmp_path):
    run, library, (retriever, worker, generator, *_) = executor(tmp_path, [SkillCandidate(NEW, 'count')], [[Observation('3')]])
    result = run.execute(INTENT)
    assert result.learned_skill == 'count_tag_in_area@v1' and library.names() == ['count_tag_in_area']
    assert 'print(' not in library.get('count_tag_in_area').code                      # the function, not the program
    retriever.retrieve.assert_called_once_with(INTENT.text, 4)
    generator.generate.assert_called_once_with(INTENT, [])
    assert worker.execute_candidate.call_args.args[2] is library                       # the run links saved Skills


def test_the_retrieved_skills_are_given_to_the_generator_and_a_call_to_one_is_recorded(tmp_path):
    library = SkillLibrary(tmp_path / 'skills'); library.add(COUNT)
    run, _, (retriever, worker, generator, *_) = executor(tmp_path, [SkillCandidate(CALLS, 'hospitals')], [[Observation('3')]],
                                                          retrieved=[library.get('count_tag_in_area')])
    result = run.execute(INTENT)
    assert generator.generate.call_args.args[1] == [library.get('count_tag_in_area')]
    assert result.retrieved_skills == ('count_tag_in_area@v1',) and result.called_skills == ('count_tag_in_area@v1',)
    assert result.learned_skill is None                                            # nothing new to save


def test_nothing_is_saved_when_the_critic_rejects(tmp_path):
    run, library, _ = executor(tmp_path, [SkillCandidate(NEW, 'count')], [[Observation('0')]], critiques=[Critique(False, 'no')])
    assert run.execute(INTENT).learned_skill is None and library.names() == []


@pytest.mark.parametrize('failures,success', [(1, True), (2, True), (3, False)])
def test_at_most_two_repairs_and_only_the_final_code_is_saved(tmp_path, failures, success):
    candidates = [SkillCandidate(NEW.replace('return 3', f'return {i}'), str(i)) for i in range(3)]
    results = [FAILURE] * failures + ([[Observation('3')]] if success else [])
    run, library, (_, _, _, critic, repairer) = executor(tmp_path, candidates, results)
    result = run.execute(INTENT)
    assert repairer.repair.call_count == min(failures, 2) and len(result.attempts) == min(failures + success, 3)
    if success:
        assert result.learned_skill == 'count_tag_in_area@v1'
        assert f'return {failures}' in library.get('count_tag_in_area').code
    else:
        assert result.failure == FAILURE and result.learned_skill is None and critic.check.call_count == 0


def test_a_function_that_calls_an_unknown_name_is_kept_out_of_the_library_with_a_note(tmp_path):
    code = 'def a(x):\n    """A."""\n    return helper(x)\n\nprint(a(1))'
    run, library, _ = executor(tmp_path, [SkillCandidate(code, 'a')], [[Observation('1')]])
    result = run.execute(INTENT)
    assert result.learned_skill is None and 'helper' in result.note and library.names() == []


@pytest.mark.parametrize('dataset_ids', [(), ('a', 'b')])
def test_an_unsupported_number_of_datasets_fails_before_retrieval(tmp_path, dataset_ids):
    run, _, (retriever, *_) = executor(tmp_path, [SkillCandidate('x', 'x')], [])
    intent = Intent('x', ('a',)); object.__setattr__(intent, 'dataset_ids', dataset_ids)
    with pytest.raises(ValueError):
        run.execute(intent)
    retriever.retrieve.assert_not_called()


def test_intent_execution_is_frozen():
    result = IntentExecution([], (), (), None, Critique(False, '未実行'))
    with pytest.raises(FrozenInstanceError):
        result.learned_skill = 'x@v1'


def test_a_copied_definition_of_a_saved_skill_is_run_as_a_call_to_it(tmp_path):
    library = SkillLibrary(tmp_path / 'skills'); library.add(COUNT)
    copied = COUNT + '\n\nprint(count_tag_in_area("amenity", "cafe", "1"))'
    run, _, (_, worker, *_) = executor(tmp_path, [SkillCandidate(copied, 'copy')], [[Observation('3')]],
                                       retrieved=[library.get('count_tag_in_area')])
    result = run.execute(INTENT)
    ran = worker.execute_candidate.call_args.args[1].code
    assert 'def count_tag_in_area' not in ran and ran == 'print(count_tag_in_area("amenity", "cafe", "1"))'
    assert result.called_skills == ('count_tag_in_area@v1',) and result.learned_skill is None
    assert library.versions('count_tag_in_area') == [1]
