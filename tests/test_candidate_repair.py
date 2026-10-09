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


def test_prompt_without_history_has_no_history_sections():
    llm = Mock(); llm.generate.return_value = REPLY
    SkillCandidateRepairer(llm).repair(Intent('対象を数える', service_ids=('overpass',)),
                                       SkillCandidate('broken', '元'), FAILURE)
    prompt = llm.generate.call_args.args[0]
    assert '試行履歴' not in prompt and '失敗した行' not in prompt


def test_prompt_with_history_shows_failing_line_and_attempt_history():
    from geo_voyager.execution_attempt import ExecutionAttempt
    llm = Mock(); llm.generate.return_value = REPLY
    stderr = 'File "<candidate>", line 2, in <module>\nKeyError: 0'
    failure = ExecutionFailure('failed', '', stderr, 73)
    history = (ExecutionAttempt('a = 1\nb = a[0]', [], failure),
               ExecutionAttempt('a = 1\nb = a[0]', [], failure))
    SkillCandidateRepairer(llm).repair(Intent('対象を数える', service_ids=('overpass',)),
                                       SkillCandidate('a = 1\nb = a[0]', '元'), failure, history=history)
    prompt = llm.generate.call_args.args[0]
    assert '>> 2: b = a[0]' in prompt
    assert '試行履歴' in prompt and '試行2: KeyError: 0（直前の試行とコードが同一）' in prompt
    assert '同じエラーが繰り返されている' in prompt


def test_executor_passes_all_candidate_attempts_so_far_to_the_repairer():
    retriever, selector, worker, generator, critic, library, repairer = [Mock() for _ in range(7)]
    retriever.retrieve.return_value = []; selector.select.return_value = None
    generator.generate.return_value = SkillCandidate('c0', '元')
    repairer.repair.side_effect = [SkillCandidate('c1', '修'), SkillCandidate('c2', '修')]
    worker.execute_candidate.side_effect = [FAILURE, FAILURE, [Observation('ok')]]
    critic.check.return_value = Critique(True, 'ok')
    with patch('geo_voyager.intent_executor.promote'):
        IntentExecutor(retriever, selector, worker, generator, critic, library, repairer=repairer).execute(
            Intent('調査', service_ids=('overpass',)))
    first, second = repairer.repair.call_args_list
    assert [a.code for a in first.kwargs['history']] == ['c0']
    assert [a.code for a in second.kwargs['history']] == ['c0', 'c1']


def test_selected_skill_attempt_is_not_part_of_the_repair_history():
    from uuid import uuid4
    from geo_voyager.skill import Skill
    retriever, selector, worker, generator, critic, library, repairer = [Mock() for _ in range(7)]
    skill = Skill(uuid4(), '既存', 'existing')
    retriever.retrieve.return_value = [skill]; selector.select.return_value = skill
    worker.execute_skill.return_value = FAILURE
    generator.generate.return_value = SkillCandidate('c0', '元')
    repairer.repair.return_value = SkillCandidate('c1', '修')
    worker.execute_candidate.side_effect = [FAILURE, [Observation('ok')]]
    critic.check.return_value = Critique(True, 'ok')
    with patch('geo_voyager.intent_executor.promote'):
        IntentExecutor(retriever, selector, worker, generator, critic, library, repairer=repairer).execute(
            Intent('調査', service_ids=('overpass',)))
    assert [a.code for a in repairer.repair.call_args.kwargs['history']] == ['c0']


def reply(code: str) -> str:
    return f'説明:\n修正した調査\n---\nコード:\n```python\n{code}\n```'


def test_unchanged_repair_is_resampled_with_a_note_and_a_higher_temperature():
    llm = Mock(); llm.generate.side_effect = [reply('broken'), reply('broken'), reply('fixed')]
    repaired = SkillCandidateRepairer(llm, max_resamples=2).repair(
        Intent('対象を数える', service_ids=('overpass',)), SkillCandidate('broken', '元'), FAILURE)
    assert repaired.code == 'fixed' and llm.generate.call_count == 3
    first, second = llm.generate.call_args_list[0], llm.generate.call_args_list[1]
    assert '元のコードと同一' not in first.args[0] and '元のコードと同一' in second.args[0]
    assert second.kwargs['temperature'] > first.kwargs['temperature']


def test_resampling_is_bounded_and_returns_the_last_candidate():
    llm = Mock(); llm.generate.return_value = reply('broken')
    repaired = SkillCandidateRepairer(llm, max_resamples=2).repair(
        Intent('対象を数える', service_ids=('overpass',)), SkillCandidate('broken', '元'), FAILURE)
    assert repaired.code == 'broken' and llm.generate.call_count == 3


def test_blank_lines_and_comments_do_not_count_as_a_change():
    llm = Mock(); llm.generate.side_effect = [reply('x = 1\n\n# note\ny = 2'), reply('z = 3')]
    repaired = SkillCandidateRepairer(llm, max_resamples=1).repair(
        Intent('対象を数える', service_ids=('overpass',)), SkillCandidate('x = 1\ny = 2', '元'), FAILURE)
    assert repaired.code == 'z = 3'


def test_default_repairer_does_not_resample():
    llm = Mock(); llm.generate.return_value = reply('broken')
    SkillCandidateRepairer(llm).repair(
        Intent('対象を数える', service_ids=('overpass',)), SkillCandidate('broken', '元'), FAILURE)
    assert llm.generate.call_count == 1


# ---- a missing required value is fixed, not hidden behind a default

ORIGINAL_CODE = 'import json\ndata = json.loads(response)\nrows = [{"value": i["value"], "count": i["count_all"]} for i in data["data"]]\nprint(json.dumps(rows))'
KEY_ERROR_FAILURE = ExecutionFailure('failed', '', 'Traceback (most recent call last):\n  File "<candidate>", line 3, in <module>\nKeyError: \'count_all\'', 73)


def code_reply(code):
    return f'説明:\n値と使用数を取得する\n---\nコード:\n```python\n{code}\n```'


def with_default(replacement='i.get("count_all", 0)'):
    return code_reply(ORIGINAL_CODE.replace('i["count_all"]', replacement))


def fixed_key():
    return code_reply(ORIGINAL_CODE.replace('count_all', 'count'))


def repair_with(replies, **kwargs):
    llm = Mock(); llm.generate.side_effect = replies
    repairer = SkillCandidateRepairer(llm, **kwargs)
    result = repairer.repair(Intent('値と使用数を取る', service_ids=('taginfo',)), SkillCandidate(ORIGINAL_CODE, '値と使用数を取得する'), KEY_ERROR_FAILURE)
    return result, repairer, llm


def test_the_right_key_is_accepted_at_once():
    result, repairer, llm = repair_with([fixed_key()])
    assert 'i["count"]' in result.code and llm.generate.call_count == 1 and repairer.rejected_fallbacks == []


def test_a_default_in_place_of_a_required_key_is_asked_again_and_the_right_key_is_taken():
    result, repairer, llm = repair_with([with_default(), fixed_key()])
    assert 'i["count"]' in result.code and llm.generate.call_count == 2
    note = llm.generate.call_args_list[1].args[0]
    assert "i.get('count_all', 0)" in note and '既定値' in note and '例外のまま' in note
    assert llm.generate.call_args_list[1].kwargs['temperature'] > llm.generate.call_args_list[0].kwargs['temperature']
    assert repairer.rejected_fallbacks == [["i.get('count_all', 0)"]]                  # the rejection is kept


def test_a_model_that_keeps_hiding_the_value_gets_the_original_code_back_so_the_failure_stays():
    result, repairer, llm = repair_with([with_default(), with_default('i.get("count_all", "")'), with_default('i.get("count_all")')])
    assert result.code == ORIGINAL_CODE and llm.generate.call_count == 3         # one try and two more, then it gives up
    assert len(repairer.rejected_fallbacks) == 3


def test_the_number_of_retries_is_bounded_and_can_be_zero():
    result, repairer, llm = repair_with([with_default()], max_default_retries=0)
    assert result.code == ORIGINAL_CODE and llm.generate.call_count == 1


def test_an_optional_get_the_original_already_had_is_not_mistaken_for_a_fallback():
    original = ORIGINAL_CODE + '\nremark = data.get("remark", "")'
    llm = Mock(); llm.generate.return_value = code_reply(original.replace('count_all', 'count'))
    repairer = SkillCandidateRepairer(llm)
    result = repairer.repair(Intent('値と使用数を取る', service_ids=('taginfo',)), SkillCandidate(original, '値と使用数を取得する'), KEY_ERROR_FAILURE)
    assert 'data.get("remark", "")' in result.code and llm.generate.call_count == 1


def test_a_new_get_for_an_optional_key_is_allowed():
    llm = Mock(); llm.generate.return_value = code_reply(ORIGINAL_CODE.replace('count_all', 'count') + '\nremark = data.get("remark")')
    result = SkillCandidateRepairer(llm).repair(Intent('値', service_ids=('taginfo',)), SkillCandidate(ORIGINAL_CODE, 'd'), KEY_ERROR_FAILURE)
    assert 'data.get("remark")' in result.code and llm.generate.call_count == 1


def test_a_handler_that_swallows_the_missing_key_is_refused_like_a_default():
    swallowing = ORIGINAL_CODE.replace('rows = [{"value": i["value"], "count": i["count_all"]} for i in data["data"]]',
                                       'rows = []\nfor i in data["data"]:\n    try:\n        rows.append({"value": i["value"], "count": i["count_all"]})\n    except KeyError:\n        pass')
    result, repairer, llm = repair_with([code_reply(swallowing), fixed_key()])
    assert 'i["count"]' in result.code and llm.generate.call_count == 2 and 'KeyError' in repairer.rejected_fallbacks[0][0]


def test_the_default_repairer_has_the_checks_on():
    assert SkillCandidateRepairer(Mock()).max_default_retries == 2


def test_the_prompt_says_to_fix_the_key_from_the_real_schema_and_not_to_hide_it():
    llm = Mock(); llm.generate.return_value = fixed_key()
    SkillCandidateRepairer(llm).repair(Intent('値', service_ids=('taginfo',)), SkillCandidate(ORIGINAL_CODE, 'd'), KEY_ERROR_FAILURE)
    prompt = llm.generate.call_args.args[0]
    for rule in ['必須フィールド', '実際の API', 'Observation の schema', '正しいキー', '.get(', '既定値で隠さない', '例外のまま', '[] アクセス', 'assert']:
        assert rule in prompt, rule
    assert 'count（使用数）' in prompt          # the schema the repair is told to check against is in the same prompt


def test_the_system_prompt_forbids_defaults_too():
    llm = Mock(); llm.generate.return_value = fixed_key()
    SkillCandidateRepairer(llm).repair(Intent('値', service_ids=('taginfo',)), SkillCandidate(ORIGINAL_CODE, 'd'), KEY_ERROR_FAILURE)
    system = llm.generate.call_args.kwargs['system_prompt']
    assert 'default' in system and 'missing' in system
