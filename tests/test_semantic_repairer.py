from unittest.mock import Mock

from geo_voyager.target_ref import TargetRef
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.semantic_repairer import SemanticRepair, SemanticRepairer

ORIGINAL = SkillCandidate('import json\nprint(json.dumps({"name": "x", "count": 0}))', '対象の件数を取得する')
REPLY = '説明:\n対象の件数を取得する\n---\nコード:\n```python\nimport json\nprint(json.dumps({"name": "x", "count": 1}))\n```'
REASON = '件数が0で、対象の地物が数えられていない'


def intent(**overrides):
    base = dict(text='港区の amenity=hospital の地物数を取得する', service_ids=('overpass',), target=TargetRef('港区'),
                previous_observations=(Observation('{"name": "港区", "relation_id": "1761717"}'),))
    base.update(overrides)
    return Intent(**base)


def repair(reply=REPLY, history=(), **kwargs):
    client = Mock(); client.generate.return_value = reply
    result = SemanticRepairer(client).repair(kwargs.pop('intent', intent()), kwargs.pop('candidate', ORIGINAL),
                                             [Observation('{"name": "港区", "count": 0}')], REASON, history=history)
    return result, client


def test_the_prompt_carries_everything_the_repair_is_allowed_to_use():
    result, client = repair()
    prompt = client.generate.call_args.args[0]
    for part in ['港区の amenity=hospital の地物数を取得する', '対象: 港区',        # intent and target
                 ORIGINAL.code, ORIGINAL.description,                                  # original candidate
                 '{"name": "港区", "count": 0}', REASON,                               # observation and critique reason
                 '"relation_id": "1761717"',                                           # previous observations
                 'overpass', 'call_service', 'load_admin_units']:                      # service and primitive contracts
        assert part in prompt, part


def test_the_prompt_forbids_changing_the_intent_and_hardcoding_answers():
    _, client = repair()
    prompt = client.generate.call_args.args[0]
    for rule in ['Intent', '対象', '出力', '固定しない']:
        assert rule in prompt
    assert 'hardcoded' in prompt or '貼り込' in prompt


def test_a_dataset_intent_gets_the_dataset_contract():
    result, client = repair(intent=intent(service_ids=(), dataset_ids=('yuiseki/jp-admin-2026-09',), target=None,
                                          previous_observations=()))
    prompt = client.generate.call_args.args[0]
    assert 'yuiseki/jp-admin-2026-09' in prompt and 'load_admin_units' in prompt


def test_a_changed_candidate_is_proposed():
    result, _ = repair()
    assert result.status == 'proposed' and 'count": 1' in result.candidate.code
    assert result.hardcoded == ()


def test_unchanged_code_is_reported_and_not_proposed():
    result, _ = repair(reply=REPLY.replace('"count": 1', '"count": 0'))
    assert result.status == 'unchanged'


def test_blank_lines_and_comments_do_not_make_a_change():
    reply = '説明:\n説明\n---\nコード:\n```python\nimport json\n\n# note\nprint(json.dumps({"name": "x", "count": 0}))\n```'
    assert repair(reply=reply)[0].status == 'unchanged'


def test_returning_to_an_earlier_attempt_is_vibration():
    earlier = ExecutionAttempt('import json\nprint(json.dumps({"name": "x", "count": 1}))', [], None)
    current = ExecutionAttempt(ORIGINAL.code, [], None)
    assert repair(history=(earlier, current))[0].status == 'vibration'


def test_a_value_copied_from_the_observations_is_rejected_as_hardcoded():
    reply = REPLY.replace('"count": 1', '"relation_id": "1761717"')
    result, _ = repair(reply=reply)
    assert result.status == 'hardcoded' and result.hardcoded == ('1761717',)


def test_a_malformed_reply_is_invalid_rather_than_an_exception():
    result, _ = repair(reply='説明だけ')
    assert result.status == 'invalid' and result.candidate is None


def test_the_model_is_asked_once_with_thinking_and_a_description_prefix():
    _, client = repair()
    assert client.generate.call_count == 1
    kwargs = client.generate.call_args.kwargs
    assert kwargs['enable_thinking'] is True and kwargs['assistant_prefix'] == '説明:\n'


def test_long_observations_are_bounded_in_the_prompt():
    client = Mock(); client.generate.return_value = REPLY
    big = Observation('{"rows": [' + ', '.join(['{"name": "区%d"}' % n for n in range(2000)]) + ']}')
    SemanticRepairer(client).repair(intent(previous_observations=(big,)), ORIGINAL, [big], REASON)
    assert len(client.generate.call_args.args[0]) < 20000


def test_primitive_contract_is_the_same_text_the_runtime_repairer_uses():
    from geo_voyager.contracts import PRIMITIVE_CONTRACT
    from geo_voyager.execution_failure import ExecutionFailure
    from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
    client = Mock(); client.generate.return_value = REPLY
    SkillCandidateRepairer(client).repair(Intent('件数', service_ids=('overpass',)), ORIGINAL,
                                          ExecutionFailure('failed', '', 'KeyError: 0', 73))
    assert PRIMITIVE_CONTRACT in client.generate.call_args.args[0]
