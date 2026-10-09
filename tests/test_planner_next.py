from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.target_ref import TargetRef
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


FIRST = Intent('港区の relation_id を取得する', service_ids=('yuisekin-geosparql',), target=TargetRef('港区'))
LOOKED_UP = entry(1, FIRST, '{"name": "港区", "relation_id": "1761717"}', targets=(TargetRef('港区', 'relation_id', '1761717'),))


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
    second = Intent('港区内の病院数', service_ids=('overpass',), target=TargetRef('港区'))
    learned, reused = uuid4(), uuid4()
    third = Intent('新宿区内の病院数', service_ids=('overpass',), target=TargetRef('新宿区'))
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


from geo_voyager.goal_history import FinalCriticFailure, PlannerFailure
from geo_voyager.planner import PlannerRejected

TWO_TARGETS = '調査項目: 両方の件数\n利用データセット: []\n利用サービス:\n  - overpass\n対象: 渋谷区\n対象: 新宿区'


def test_an_unusable_reply_is_rejected_with_its_reason_and_the_reply_that_caused_it():
    plan, client = planner(TWO_TARGETS)
    with pytest.raises(PlannerRejected) as raised:
        plan.next('g', GoalHistory())
    assert isinstance(raised.value, ValueError)                  # callers that catch ValueError still work
    assert 'more than one 対象' in raised.value.reason and raised.value.reply == TWO_TARGETS
    assert client.generate.call_count == 1                       # a rejection is not retried inside next()


def test_every_kind_of_unusable_reply_carries_its_reply():
    for reply in ('ただの文章', STEP.replace('yuisekin-geosparql', 'unknown'), STEP.replace('利用サービス:', 'service:'), LOCAL):
        with pytest.raises(PlannerRejected) as raised:
            planner(reply)[0].next('g', GoalHistory())
        assert raised.value.reply == reply and raised.value.reason


def test_an_empty_goal_is_not_a_planner_failure():
    with pytest.raises(ValueError) as raised:
        planner(STEP)[0].next(' ', GoalHistory())
    assert not isinstance(raised.value, PlannerRejected)


def test_a_planner_failure_in_the_history_is_shown_with_its_reason_and_what_was_written():
    h = history(LOOKED_UP)
    h.append(PlannerFailure('ValueError: An Intent has more than one 対象 line', reply=TWO_TARGETS, after_step=1))
    plan, client = planner(NEXT)
    plan.next('g', h)
    prompt = client.generate.call_args.args[0]
    for shown in ['計画の失敗', 'more than one 対象', '対象: 渋谷区', '対象: 新宿区']:
        assert shown in prompt, shown


def test_a_final_critic_failure_in_the_history_is_shown_with_the_critics_reason():
    h = history(LOOKED_UP)
    h.append(FinalCriticFailure('上位3つの値が示されていない', after_step=1))
    plan, client = planner(NEXT)
    plan.next('g', h)
    prompt = client.generate.call_args.args[0]
    assert 'Goal の最終判定が未達' in prompt and '上位3つの値が示されていない' in prompt


def test_failures_appear_between_the_steps_in_the_order_they_happened():
    h = history(LOOKED_UP)
    h.append(PlannerFailure('bad plan one', after_step=1))
    second = Intent('港区の件数', service_ids=('overpass',), target=TargetRef('港区'))
    h.append(entry(2, second, '{"count": 22}'))
    h.append(FinalCriticFailure('late reason', after_step=2))
    plan, client = planner(NEXT)
    plan.next('g', h)
    prompt = client.generate.call_args.args[0]
    assert prompt.index('step 1') < prompt.index('bad plan one') < prompt.index('step 2') < prompt.index('late reason')


def test_a_history_of_failures_only_still_says_nothing_was_executed():
    h = GoalHistory()
    h.append(PlannerFailure('bad plan', after_step=0))
    plan, client = planner(STEP)
    plan.next('g', h)
    prompt = client.generate.call_args.args[0]
    assert 'まだ何も実行していない' in prompt and 'bad plan' in prompt


def test_the_prompt_tells_the_model_how_to_recover_from_each_kind_of_failure():
    plan, client = planner(NEXT)
    plan.next('g', history(LOOKED_UP))
    prompt = client.generate.call_args.args[0]
    for rule in ['計画の失敗', '最終判定が未達', '同じ DONE を繰り返さない', '対象ごとに Intent を分ける']:
        assert rule in prompt, rule


# ---- the Planner sees the whole service contract, and does not write how to call a service

from geo_voyager.services import load_service_graph

HOW = '調査項目: taginfo API /api/4/keys/cuisine/values に limit=3 を指定して上位3件を取得する\n利用データセット: []\n利用サービス:\n  - taginfo'
WHAT = '調査項目: cuisine キーの値を使用数の多い順に並べ、上位3つを求める\n利用データセット: []\n利用サービス:\n  - taginfo'


def test_the_prompt_shows_every_service_description_in_full():
    plan, client = planner(WHAT)
    plan.next('g', GoalHistory())
    prompt = client.generate.call_args.args[0]
    for service in load_service_graph().all():
        for sentence in service.description.split('。'):
            if sentence.strip():
                assert sentence in prompt, (service.id, sentence)
    assert '/api/4/key/values は key を受け取る' in prompt          # the endpoint the first-plan prompt cut off


def test_the_first_plan_prompt_is_still_the_short_one():
    client = Mock(); client.generate.return_value = STEP
    Planner(client).plan_goal('ゴール')
    assert '/api/4/key/values' not in client.generate.call_args.args[0]


def test_an_intent_that_names_an_endpoint_or_a_parameter_is_rejected_with_what_it_named():
    plan, client = planner(HOW)
    with pytest.raises(PlannerRejected) as raised:
        plan.next('g', GoalHistory())
    reason = raised.value.reason
    assert '/api/4/keys/cuisine/values' in reason and 'limit=3' in reason and '何を調べるか' in reason
    assert raised.value.reply == HOW and client.generate.call_count == 1       # still one model call


def test_an_intent_that_says_what_to_find_is_accepted_even_with_an_osm_tag_in_it():
    result = planner(WHAT)[0].next('g', GoalHistory())
    assert result.text.startswith('cuisine キーの値') and result.service_ids == ('taginfo',)
    tag = '調査項目: 渋谷区の amenity=cafe の OSM 地物数を求める\n利用データセット: []\n利用サービス:\n  - overpass'
    assert planner(tag)[0].next('g', GoalHistory()).service_ids == ('overpass',)


def test_the_rejection_is_kept_in_the_history_so_the_planner_can_write_it_again():
    from geo_voyager.goal_history import PlannerFailure
    plan, client = planner(HOW)
    with pytest.raises(PlannerRejected) as raised:
        plan.next('g', GoalHistory())
    history = GoalHistory()
    history.append(PlannerFailure(raised.value.reason, raised.value.reply))
    plan2, client2 = planner(WHAT)
    plan2.next('g', history)
    prompt = client2.generate.call_args.args[0]
    assert '計画の失敗' in prompt and '/api/4/keys/cuisine/values' in prompt and 'limit=3' in prompt


def test_the_prompt_tells_the_planner_to_say_what_to_find_and_not_how_to_call():
    plan, client = planner(WHAT)
    plan.next('g', GoalHistory())
    prompt = client.generate.call_args.args[0]
    for rule in ['API のパス', 'パラメータ', '書かない', '呼び方は実行側が決める']:
        assert rule in prompt, rule
