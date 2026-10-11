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


def test_the_prompt_counts_how_often_each_resource_was_used_and_names_the_unused_ones():
    agent, client = curriculum('Goal: x を求める\n理由: y')
    agent.propose([FINDING, dict(FINDING, goal='b', resources=['overpass', 'yuisekin-geosparql'])], [])
    prompt = client.generate.call_args.args[0]
    assert 'overpass: 2 件' in prompt and 'yuisekin-geosparql: 1 件' in prompt
    unused = prompt.split('まだ使っていないリソース:', 1)[1].split('\n', 1)[0]
    for resource in ('yuiseki/jp-admin-2026-09', 'yuiseki/worldpop-jp-2026-01', 'nominatim', 'valhalla', 'taginfo'):
        assert resource in unused
    assert 'overpass' not in unused


def test_the_prompt_asks_for_questions_about_the_world_not_about_identifiers_and_for_a_new_kind_of_question():
    agent, client = curriculum('Goal: x を求める\n理由: y')
    agent.propose([FINDING], [])
    prompt = client.generate.call_args.args[0]
    for text in ('識別子', '何を表すか', '同じ型の問い', 'まだ使っていないリソース'):
        assert text in prompt


def test_the_history_shown_stays_within_a_length_budget_newest_first():
    from geo_voyager.curriculum import HISTORY_CHARS
    agent, client = curriculum('Goal: x を求める\n理由: y')
    long = 'あ' * 280
    findings = [dict(FINDING, goal=f'goal {n} {long}', answer=long) for n in range(20)]
    attempts = [dict(ATTEMPT, goal=f'attempt {n} {long}', reason=long) for n in range(15)]
    agent.propose(findings, attempts)
    prompt = client.generate.call_args.args[0]
    history = prompt[prompt.index('これまでの発見:'):prompt.index('OUTPUT:')]
    assert len(history) <= HISTORY_CHARS
    assert 'goal 19 ' in history and 'attempt 14 ' in history
    assert 'goal 0 ' not in history and 'attempt 0 ' not in history
    assert history.index('goal 18 ') < history.index('goal 19 ')
