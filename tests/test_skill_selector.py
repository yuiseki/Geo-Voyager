from unittest.mock import Mock
from uuid import UUID

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill import Skill
from geo_voyager.skill_selector import SkillSelector


MAX = Skill(UUID('72c549dd-e449-4bef-97f1-e3a2eab27d64'), '人口最大の区域と人口を求める', 'SECRET_MAX_CODE')
MIN = Skill(UUID('e722f367-1ff1-4796-89a3-48cfd1dfcb68'), '人口最小の区域と人口を求める', 'SECRET_MIN_CODE')


def test_empty_candidates_do_not_call_llm():
    client = Mock()
    assert SkillSelector(client).select(Intent('人口最大', ('admin',)), []) is None
    client.generate.assert_not_called()


@pytest.mark.parametrize('text,skills,selection', [
    ('人口最大の区域と人口', [MIN, MAX], MAX),
    ('人口最小の区域と人口', [MAX, MIN], MIN),
    ('人口最大の区域と人口', [MAX, MIN], MAX),
    ('鉄道駅数を求める', [MAX, MIN], None),
    ('鉄道駅数を求める', [MAX], None),
])
def test_select_with_llm_and_prompt_contains_only_candidate_metadata(text, skills, selection):
    client = Mock()
    client.generate.return_value = f'選択: {selection.id if selection else "なし"}\n理由: 要求との一致を確認したため。'
    intent = Intent(text, ('DATASET_SECRET',))
    assert SkillSelector(client).select(intent, skills) is selection
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    assert text in prompt
    for skill in skills:
        assert str(skill.id) in prompt
        assert skill.description in prompt
        assert skill.code not in prompt
    assert 'DATASET_SECRET' not in prompt


@pytest.mark.parametrize('output', [
    '選択: 11111111-1111-4111-8111-111111111111\n理由: 一致',
    '選択: invalid-uuid\n理由: 一致',
    '選択: なし',
    '選択: なし\n理由:',
    '選択: なし\n理由: 一致\n余分な行',
    'UUID: なし\n理由: 一致',
    '選択: なし\n説明: 一致',
])
def test_invalid_or_unknown_selection_is_rejected(output):
    client = Mock()
    client.generate.return_value = output
    with pytest.raises(ValueError):
        SkillSelector(client).select(Intent('人口最大', ('admin',)), [MAX, MIN])


def test_selector_prompt_requires_direct_execution_and_explicit_none_format():
    client = Mock()
    client.generate.return_value = '選択: なし\n理由: 該当なし'
    assert SkillSelector(client).select(Intent('平均人口を求める', ('admin',)), [MAX, MIN]) is None
    prompt = client.generate.call_args.args[0]
    assert 'コードの変更や追加計算が必要なら「なし」' in prompt
    assert '選択: なし\n理由:' in prompt


def test_selector_uses_zero_temperature_for_candidate_judgement():
    client = Mock()
    client.generate.return_value = f'選択: {MAX.id}\n理由: 一致する'
    SkillSelector(client).select(Intent('人口最大', ('admin',)), [MAX])
    assert client.generate.call_args.kwargs['temperature'] == 0.0
