from unittest.mock import Mock

import pytest

from geo_voyager.curriculum import Curriculum, CurriculumRejected, ProposedGoal


def curriculum(reply):
    client = Mock(); client.generate.return_value = reply
    return Curriculum(client), client


FINDING = {'goal': '渋谷区のカフェの数', 'answer': '{"tag": "amenity=cafe", "count": 459}', 'critic_reason': 'ok',
           'steps': [], 'resources': ['overpass'], 'targets': [{'name': '渋谷区', 'id_type': 'relation_id', 'id_value': '1759477'}]}
ATTEMPT = {'goal': '23区で最も人口の多い区', 'success': False, 'stop_reason': 'max_steps', 'reason': 'Goal を完了できなかった: max_steps'}


def test_the_curriculum_proposes_one_goal_with_its_reason():
    agent, client = curriculum('Goal: 新宿区の amenity=cafe の数を求める\n理由: 渋谷区と比べる材料にする')
    proposed = agent.propose([FINDING], [ATTEMPT])
    assert proposed == ProposedGoal('新宿区の amenity=cafe の数を求める', '渋谷区と比べる材料にする')
    prompt = client.generate.call_args.args[0]
    for text in ('渋谷区のカフェの数', '"count": 459', '渋谷区 (relation_id=1759477)', '23区で最も人口の多い区', 'max_steps',
                 'Service overpass', 'Dataset yuiseki/jp-admin-2026-09', '少しずつ難しく', 'まだ分かっていない'):
        assert text in prompt


def test_the_prompt_starts_from_nothing_when_nothing_is_known():
    agent, client = curriculum('Goal: 東京23区の区の数を求める\n理由: 最初の足場')
    agent.propose([], [])
    assert 'まだ何も分かっていない' in client.generate.call_args.args[0]


def test_only_the_latest_findings_and_attempts_are_shown():
    agent, client = curriculum('Goal: x を求める\n理由: y')
    findings = [dict(FINDING, goal=f'goal {n}') for n in range(50)]
    agent.propose(findings, [dict(ATTEMPT, goal=f'attempt {n}') for n in range(50)])
    prompt = client.generate.call_args.args[0]
    assert 'goal 49' in prompt and 'goal 0\n' not in prompt and 'goal 10\n' not in prompt
    assert 'attempt 49' in prompt and 'attempt 10\n' not in prompt


@pytest.mark.parametrize('reply', [
    '', '新宿区のカフェの数', 'Goal: \n理由: y', 'Goal: x を求める', 'Goal: a\nGoal: b\n理由: y',
    'Goal: 渋谷区のカフェの数\n理由: もう一度',
    'Goal: /api/interpreter で渋谷区のカフェを数える\n理由: y',
])
def test_an_unusable_or_repeated_goal_is_rejected(reply):
    agent, _ = curriculum(reply)
    with pytest.raises(CurriculumRejected):
        agent.propose([FINDING], [])


def test_a_rejection_note_is_shown_on_the_next_call():
    agent, client = curriculum('Goal: x を求める\n理由: y')
    agent.propose([], [], note='前回の応答は使えなかった: Goal: の行が無い')
    assert '前回の応答は使えなかった: Goal: の行が無い' in client.generate.call_args.args[0]
