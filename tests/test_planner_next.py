from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.critique import Critique
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.goal_history import GoalHistory, HistoryEntry
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.planner import DONE, Done, Planner

STEP = '調査項目: 港区の relation_id を取得する\n利用データセット: []\n利用サービス:\n  - yuisekin-geosparql\n対象: 港区'
NEXT = '調査項目: 港区内の amenity=hospital の地物数を取得する\n利用データセット: []\n利用サービス:\n  - overpass\n対象: 港区'
LOCAL = '調査項目: 前段の件数を比べる\n利用データセット: []\n利用サービス: []'


def planner(reply):
    client = Mock(); client.generate.return_value = reply
    return Planner(client), client


def entry(step, intent, obs='', ok=True, failure=None, critic='ok', reused=None, learned=None, targets=()):
    return HistoryEntry(step, intent, (Observation(obs),) if obs else (), Critique(ok, critic), failure, reused, learned, targets)


def history(*entries):
    result = GoalHistory()
    for item in entries:
        result.append(item)
    return result


FIRST = Intent('港区の relation_id を取得する', service_ids=('yuisekin-geosparql',), target_name='港区')
LOOKED_UP = entry(1, FIRST, '{"name": "港区", "relation_id": "1761717"}', targets=({'name': '港区', 'relation_id': '1761717'},))


def test_done_is_an_explicit_value():
    assert isinstance(DONE, Done) and DONE == Done() and repr(DONE) == 'DONE'


def test_the_first_call_decides_one_intent_from_the_goal_alone():
    plan, client = planner(STEP)
    result = plan.next('港区の病院数を求める', GoalHistory())
    assert isinstance(result, Intent) and result.service_ids == ('yuisekin-geosparql',) and result.target_name == '港区'
    assert client.generate.call_count == 1
    prompt = client.generate.call_args.args[0]
    assert '港区の病院数を求める' in prompt and 'まだ何も実行していない' in prompt


def test_each_call_asks_the_model_once_and_returns_at_most_one_intent():
    plan, client = planner(STEP + '\n---\n' + NEXT)
    result = plan.next('港区の病院数を求める', GoalHistory())
    assert client.generate.call_count == 1 and result.text.startswith('港区の relation_id')   # the first block only


def test_the_model_can_say_done():
    for reply in ('DONE', '  DONE  ', 'DONE\n理由: 揃った'):
        assert planner(reply)[0].next('g', history(LOOKED_UP)) is DONE


def test_a_reply_that_only_mentions_done_is_not_done():
    with pytest.raises(ValueError):
        planner('DONEではない説明')[0].next('g', history(LOOKED_UP))


def test_the_prompt_shows_what_the_history_holds():
    failure = ExecutionFailure('failed', '', 'Traceback\nKeyError: 0', 73)
    second = Intent('港区内の病院数', service_ids=('overpass',), target_name='港区')
    learned, reused = uuid4(), uuid4()
    third = Intent('新宿区内の病院数', service_ids=('overpass',), target_name='新宿区')
    plan, client = planner(DONE.__repr__())
    plan.next('港区の病院数を求める', history(
        LOOKED_UP,
        entry(2, second, '', ok=False, failure=failure, critic='Generated Python execution failed'),
        entry(3, third, '{"name": "新宿区", "count": 12}', critic='件数が答えられている', reused=reused, learned=learned)))
    prompt = client.generate.call_args.args[0]
    for shown in ['港区の relation_id を取得する', '"relation_id": "1761717"',          # intent and observation
                  '港区内の病院数', 'KeyError: 0', 'Generated Python execution failed',  # a failed step and why
                  '件数が答えられている',                                              # the Critic's verdict
                  str(reused)[:8], str(learned)[:8],                                    # skill reused and learned
                  '判明した対象', '港区', '1761717']:                                    # the targets made known
        assert shown in prompt, shown


def test_the_prompt_tells_the_model_how_to_use_known_targets_and_when_to_stop():
    plan, client = planner(NEXT)
    plan.next('g', history(LOOKED_UP))
    prompt = client.generate.call_args.args[0]
    for rule in ['DONE', '対象: 名前', '繰り返さない', '1件だけ']:
        assert rule in prompt, rule


def test_a_target_first_made_known_by_an_earlier_step_can_name_the_next_intent():
    plan, _ = planner(NEXT)
    result = plan.next('港区の病院数を求める', history(LOOKED_UP))
    assert result.target_name == '港区' and result.service_ids == ('overpass',)


def test_a_local_step_needs_earlier_observations_to_work_on():
    with pytest.raises(ValueError, match='external resource'):
        planner(LOCAL)[0].next('g', GoalHistory())
    with pytest.raises(ValueError, match='external resource'):
        planner(LOCAL)[0].next('g', history(entry(1, FIRST, '', ok=False)))        # nothing succeeded yet
    assert planner(LOCAL)[0].next('g', history(LOOKED_UP)).requires_context is True


def test_an_unregistered_resource_or_a_malformed_reply_is_rejected():
    for reply in (STEP.replace('yuisekin-geosparql', 'unknown'), 'ただの文章', STEP.replace('利用サービス:', 'service:')):
        with pytest.raises((ValueError, KeyError)):
            planner(reply)[0].next('g', GoalHistory())


def test_an_empty_goal_is_rejected_before_asking_the_model():
    plan, client = planner(STEP)
    with pytest.raises(ValueError):
        plan.next('  ', GoalHistory())
    client.generate.assert_not_called()


def test_a_long_observation_is_bounded_in_the_prompt():
    plan, client = planner(NEXT)
    plan.next('g', history(entry(1, FIRST, '{"rows": [' + ', '.join(['1'] * 5000) + ']}')))
    assert len(client.generate.call_args.args[0]) < 12000


def test_the_history_is_not_changed_by_planning():
    plan, _ = planner(NEXT)
    h = history(LOOKED_UP)
    plan.next('g', h)
    assert len(h) == 1
