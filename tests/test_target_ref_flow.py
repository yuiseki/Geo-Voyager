"""The stable id decides which target a step is about. The name is for showing, and for a first look-up."""
from dataclasses import asdict
import json
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from geo_voyager.critic import Critic
from geo_voyager.critique import Critique
from geo_voyager.goal_history import GoalHistory, HistoryEntry, intent_key, render_history
from geo_voyager.intent import Intent
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation
from geo_voyager.planner import Planner, PlannerRejected
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.target_ref import TargetRef
from geo_voyager.worker import Worker

MINATO = TargetRef('港区', 'relation_id', '1761717')
MINATO_LONG = TargetRef('港区, 東京都, 日本', 'relation_id', '1761717')
VALID = '説明:\nS\n---\nコード:\n```python\ndef answer():\n    """Answer."""\n    return 1\n```'


def obs(value) -> Observation:
    return Observation(json.dumps(value, ensure_ascii=False))


def intent(target, **kwargs):
    return Intent('港区の件数を取得する', service_ids=('overpass',), target=target, **kwargs)


# ---- a different display name, the same id: it is the same target

def test_the_critic_asks_the_model_when_the_id_matches_whatever_the_name():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ID が一致する'
    result = Critic(client).check(intent(MINATO), [obs({'name': '港区, 東京都, 日本', 'relation_id': 1761717, 'count': 22})])
    assert result.success and client.generate.call_count == 1
    prompt = client.generate.call_args.args[0]
    assert 'relation_id=1761717' in prompt and '名前は表示' in prompt


def test_the_critic_shows_the_target_it_found_by_id_under_another_display_name():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    previous = (obs({'name': '港区, 東京都, 日本', 'relation_id': '1761717'}),)
    Critic(client).check(intent(MINATO, previous_observations=previous), [obs({'relation_id': '1761717', 'count': 22})])
    prompt = client.generate.call_args.args[0]
    assert '解決済み参照対象: {"name": "港区, 東京都, 日本", "id_type": "relation_id", "id_value": "1761717"}' in prompt
    assert 'ID が一致した' in prompt


def test_the_planner_resolves_a_short_name_to_the_known_target_with_its_id():
    history = GoalHistory()
    history.append(HistoryEntry(1, Intent('港区の ID', service_ids=('nominatim',), target=TargetRef('港区')),
                                (obs({'name': '港区, 東京都, 日本', 'relation_id': 1761717}),), Critique(True, 'ok'), None, None, None,
                                (MINATO_LONG,)))
    client = Mock(); client.generate.return_value = '調査項目: 港区の件数\n利用データセット: []\n利用サービス:\n  - overpass\n対象: 港区'
    result = Planner(client).next('g', history)
    assert result.target == MINATO_LONG and result.target.resolved             # the id came along, the display name is the known one


# ---- the same name, another id: it is another target, and it is refused

def test_the_critic_fails_an_observation_about_another_id_without_asking_the_model():
    client = Mock()
    result = Critic(client).check(intent(MINATO), [obs({'name': '港区', 'relation_id': '3554304', 'count': 5})])
    assert not result.success and '3554304' in result.reason and '1761717' in result.reason
    client.generate.assert_not_called()


def test_a_name_known_under_two_ids_is_refused_by_the_planner_with_the_ids_listed():
    history = GoalHistory()
    nagoya = TargetRef('港区, 名古屋市, 愛知県, 日本', 'relation_id', '3554304')
    history.append(HistoryEntry(1, Intent('港区を探す', service_ids=('nominatim',), target=TargetRef('港区')),
                                (obs([{'name': '港区, 東京都, 日本', 'relation_id': 1761717}, {'name': nagoya.name, 'relation_id': 3554304}]),),
                                Critique(True, 'ok'), None, None, None, (MINATO_LONG, nagoya)))
    client = Mock(); client.generate.return_value = '調査項目: 港区の件数\n利用データセット: []\n利用サービス:\n  - overpass\n対象: 港区'
    with pytest.raises(PlannerRejected) as raised:
        Planner(client).next('g', history)
    assert '1761717' in raised.value.reason and '3554304' in raised.value.reason and 'ID' in raised.value.reason
    client.generate.return_value = client.generate.return_value.replace('対象: 港区', '対象: relation_id=3554304')
    assert Planner(client).next('g', history).target == nagoya                  # named by its id, it is clear


# ---- the TargetRef a step found is the one the next step uses

def test_the_history_carries_the_ref_a_step_found_and_the_planner_is_shown_its_id():
    history = GoalHistory()
    execution = IntentExecution([obs({'name': '港区, 東京都, 日本', 'relation_id': 1761717})], (), (), None, Critique(True, 'ok'))
    history.append(HistoryEntry.from_execution(1, Intent('港区の ID', service_ids=('nominatim',), target=TargetRef('港区')), execution, history))
    assert history.targets() == (MINATO_LONG,) and history.entries[0].targets == (MINATO_LONG,)
    text = render_history(history)
    assert '港区, 東京都, 日本 (relation_id=1761717)' in text and 'ID で区別する' in text


def test_the_same_id_under_another_display_name_is_not_a_new_target():
    history = GoalHistory()
    for step, name in ((1, '港区, 東京都, 日本'), (2, '港区')):
        execution = IntentExecution([obs({'name': name, 'relation_id': 1761717})], (), (), None, Critique(True, 'ok'))
        history.append(HistoryEntry.from_execution(step, Intent(f'step {step}', service_ids=('nominatim',)), execution, history))
    assert [t.name for t in history.targets()] == ['港区, 東京都, 日本'] and history.entries[1].targets == ()


def test_two_intents_about_the_same_id_are_the_same_step_whatever_the_display_name():
    assert intent_key(intent(MINATO)) == intent_key(intent(MINATO_LONG))
    assert intent_key(intent(MINATO)) != intent_key(intent(TargetRef('港区', 'relation_id', '3554304')))
    assert intent_key(intent(TargetRef('港区'))) != intent_key(intent(MINATO))            # a name to look up is not an id


def test_the_ref_of_an_intent_is_kept_in_the_record_of_the_run():
    record = asdict(intent(MINATO))
    assert record['target'] == {'name': '港区', 'id_type': 'relation_id', 'id_value': '1761717'}


# ---- what the worker and the generator give the code

def run_worker(target, previous=()):
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = 'ok'
        Worker('internal').execute_candidate(intent(target, previous_observations=previous), SkillCandidate('print(1)', 's'))
    return sandbox.return_value.run.call_args.args[0]


def test_the_worker_hands_the_code_the_id_of_a_resolved_target_and_only_the_name_of_an_unresolved_one():
    assert "intent_target={'name': '港区', 'id_type': 'relation_id', 'id_value': '1761717'}" in run_worker(MINATO)
    assert "intent_target={'name': '港区'}" in run_worker(TargetRef('港区'))


def generation_prompt(target, previous=()):
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(intent(target, previous_observations=previous))
    return client.generate.call_args.args[0]


def test_the_generator_tells_the_code_to_find_a_resolved_target_by_id_and_not_by_name():
    prompt = generation_prompt(MINATO, (Observation('[]'),))
    assert 'str(t.get(intent_target["id_type"])) == intent_target["id_value"]' in prompt
    assert '名前の一致で対象を選ばない' in prompt and '同じ名前でも ID が違う object は別の対象' in prompt
    assert 't.get("name") == intent_target["name"]' not in prompt


def test_the_generator_still_looks_an_unresolved_target_up_by_name():
    prompt = generation_prompt(TargetRef('港区'), (Observation('[]'),))
    assert 't.get("name") == intent_target["name"]' in prompt and 'id_value' not in prompt.split('Intent:')[-1]


def test_the_generator_system_prompt_makes_the_id_the_key_and_the_name_for_display():
    client = Mock(); client.generate.return_value = VALID
    SkillCandidateGenerator(client).generate(intent(MINATO))
    system = client.generate.call_args.kwargs['system_prompt']
    assert 'id_value' in system and 'only for display' in system
