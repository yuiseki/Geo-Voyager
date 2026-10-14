import json
from geo_voyager.critique import Critique
from geo_voyager.goal_executor import AdaptiveGoalExecution
from geo_voyager.goal_history import HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.target_ref import TargetRef
from geo_voyager.world_graph import WorldGraph

SHIBUYA = TargetRef('渋谷区', 'relation_id', '1759477')


def entry(step, text, obs, ok=True, targets=(), services=('overpass',)):
    return HistoryEntry(step, Intent(text, service_ids=services), (Observation(obs),) if obs else (),
                        Critique(ok, 'ok' if ok else 'ng'), None, (), None, targets)


def execution(goal, entries, stop='done', success=True):
    return AdaptiveGoalExecution(goal, tuple(entries), (), stop, Critique(success, '答えが出ている' if success else '未達'))


def test_a_goal_that_ended_done_and_passed_the_final_critic_becomes_a_finding_with_its_provenance(tmp_path):
    world = WorldGraph(tmp_path / 'world.jsonl')
    result = execution('渋谷区のカフェの数', [
        entry(1, '渋谷区の relation_id', '{"name": "渋谷区", "relation_id": "1759477"}', targets=(SHIBUYA,),
              services=('yuisekin-geosparql',)),
        entry(2, '失敗した step', '{"count": 0}', ok=False),
        entry(3, '渋谷区の amenity=cafe の数', '{"tag": "amenity=cafe", "count": 459}'),
    ])
    finding = world.record(result, explored_at='2026-10-11T07:00:00')
    assert finding['goal'] == '渋谷区のカフェの数'
    assert finding['answer'] == '{"tag": "amenity=cafe", "count": 459}'
    assert '答えが出ている' not in json.dumps(finding, ensure_ascii=False)        # no Critic's words are kept (ADR 0011)
    assert [step['intent'] for step in finding['steps']] == ['渋谷区の relation_id', '渋谷区の amenity=cafe の数']
    assert finding['resources'] == ['yuisekin-geosparql', 'overpass']
    assert finding['targets'] == [{'name': '渋谷区', 'id_type': 'relation_id', 'id_value': '1759477'}]
    assert finding['explored_at'] == '2026-10-11T07:00:00'
    assert WorldGraph(tmp_path / 'world.jsonl').findings() == [finding]


def test_a_goal_that_did_not_pass_is_not_a_finding(tmp_path):
    world = WorldGraph(tmp_path / 'world.jsonl')
    assert world.record(execution('g', [entry(1, 'a', '{"count": 1}')], stop='max_steps', success=False)) is None
    assert world.record(execution('g', [entry(1, 'a', '{"count": 1}', ok=False)])) is None
    assert world.findings() == []


def test_targets_are_known_once_by_their_id_across_findings(tmp_path):
    world = WorldGraph(tmp_path / 'world.jsonl')
    world.record(execution('a', [entry(1, 'x', '{"count": 1}', targets=(SHIBUYA,))]))
    world.record(execution('b', [entry(1, 'y', '{"count": 2}', targets=(TargetRef('渋谷区, 東京都', 'relation_id', '1759477'),
                                                                        TargetRef('新宿区', 'relation_id', '1758858')))]))
    assert world.targets() == [SHIBUYA, TargetRef('新宿区', 'relation_id', '1758858')]
