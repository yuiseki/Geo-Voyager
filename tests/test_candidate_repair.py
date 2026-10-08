from unittest.mock import Mock, patch
import pytest

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer


FAILURE = ExecutionFailure('Python failed', 'partial output', 'SyntaxError: broken', 73)
REPLY = '説明:\n修正した調査\n---\nコード:\n```python\nprint("result")\n```'


def test_repair_prompt_and_strict_candidate_parser():
    llm = Mock(); llm.generate.return_value = REPLY
    intent = Intent('対象を数える', service_ids=('overpass',))
    original = SkillCandidate('broken', '元の説明')
    repaired = SkillCandidateRepairer(llm).repair(intent, original, FAILURE)
    assert repaired == SkillCandidate('print("result")', '修正した調査')
    prompt = llm.generate.call_args.args[0]
    for text in [intent.text, 'overpass', original.code, original.description,
                 FAILURE.stdout, FAILURE.stderr, '73', 'call_service', 'hardcoded answer', 'Intent を変更しない']:
        assert text in prompt
    assert 'https://overpass.yuiseki.net' not in prompt
    llm.generate.return_value = 'invalid'
    with pytest.raises(ValueError):
        SkillCandidateRepairer(llm).repair(intent, original, FAILURE)


@pytest.mark.parametrize('failures,success', [(1, True), (2, True), (3, False)])
def test_bounded_repairs_only_save_success_and_skip_critic_on_execution_failure(failures, success):
    retriever, selector, worker, generator, critic, library, repairer = [Mock() for _ in range(7)]
    retriever.retrieve.return_value = []; selector.select.return_value = None
    original = SkillCandidate('original', '元'); repaired = SkillCandidate('repaired', '修正')
    generator.generate.return_value = original; repairer.repair.return_value = repaired
    worker.execute_candidate.side_effect = [FAILURE] * failures + ([[Observation('result')]] if success else [])
    critic.check.return_value = Critique(True, 'answered')
    executor = IntentExecutor(retriever, selector, worker, generator, critic, library, repairer=repairer)
    with patch('geo_voyager.intent_executor.promote') as promote:
        result = executor.execute(Intent('調査', service_ids=('overpass',)))
    assert repairer.repair.call_count == min(failures, 2)
    assert worker.execute_candidate.call_count == min(failures + 1, 3)
    assert result.critique.success == success
    assert critic.check.call_count == int(success)
    assert library.add.call_count == int(success)
    assert promote.call_count == int(success)
    if success:
        promote.assert_called_once_with(repaired)
    else:
        assert result.failure == FAILURE and result.learned_skill_id is None


def test_only_final_repaired_source_is_saved_to_real_library(tmp_path):
    from geo_voyager.skill import SkillLibrary
    retriever, selector, worker, generator, critic, repairer = [Mock() for _ in range(6)]
    retriever.retrieve.return_value = []; selector.select.return_value = None
    generator.generate.return_value = SkillCandidate('broken original', '元の説明')
    fixed = SkillCandidate('print("answer")', '修正された操作')
    repairer.repair.return_value = fixed
    worker.execute_candidate.side_effect = [FAILURE, [Observation('answer')]]
    critic.check.return_value = Critique(True, 'answered')
    library = SkillLibrary(tmp_path)
    result = IntentExecutor(retriever, selector, worker, generator, critic, library, repairer).execute(
        Intent('調査', service_ids=('overpass',)))
    assert len(library.all()) == 1
    saved = library.get(result.learned_skill_id)
    assert saved.code == fixed.code and saved.description == fixed.description
    assert result.attempts[0].code == 'broken original'
    assert result.attempts[1].code == fixed.code


def test_repair_is_direct_code_correction_with_short_description():
    llm = Mock(); llm.generate.return_value = REPLY
    SkillCandidateRepairer(llm).repair(Intent('調査', service_ids=('overpass',)), SkillCandidate('bad', '操作'), FAILURE)
    options = llm.generate.call_args.kwargs
    assert 'one sentence' in options['system_prompt']
    assert options['temperature'] > 0


def test_repair_preserves_description_scope():
    llm = Mock(); llm.generate.return_value = REPLY
    SkillCandidateRepairer(llm).repair(Intent('調査', service_ids=('overpass',)), SkillCandidate('bad', '操作'), FAILURE)
    assert 'Preserve the original description' in llm.generate.call_args.kwargs['system_prompt']


def test_repair_receives_nested_service_json_contracts():
    llm = Mock(); llm.generate.return_value = REPLY
    SkillCandidateRepairer(llm).repair(Intent('API調査', service_ids=('taginfo','yuisekin-geosparql')), SkillCandidate('bad', '操作'), FAILURE)
    prompt = llm.generate.call_args.args[0]
    assert 'payload["data"]' in prompt and 'payload["results"]["bindings"]' in prompt
