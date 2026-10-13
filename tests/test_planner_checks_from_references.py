"""Two errors stage 1 kept making, whatever the wording of the dataset lines: asking a dataset for an id it does
not have, and writing codes into an Intent that neither the Goal nor the history gave. They are refused without the
model, so a change of wording can not bring them back."""
import pytest

from geo_voyager.goal_history import GoalHistory
from geo_voyager.planner import PlannerRejected
from test_named_results import LISTED, planner

GOAL = '東京23区で隣接する区対のうち、2020年総人口の合計が最大の区対の合計人口は何人か'


def reply(text, datasets=('yuiseki/jp-admin-2026-09',), services=(), inputs=()):
    listed = lambda items: (''.join(f'\n  - {item}' for item in items)) if items else ' []'
    return (f'調査項目: {text}\n結果名: step_result\n入力:{listed(inputs)}\n'
            f'利用データセット:{listed(datasets)}\n利用サービス:{listed(services)}')


def test_an_id_the_only_dataset_lacks_is_refused_with_the_references_note():
    # stage1_c15bbe1, Goal 10.
    model, _ = planner(reply('東京23区の全23区について、日本語名称、OSM relation_id、2020年国勢調査人口を1行ずつ一覧で取得する'))
    with pytest.raises(PlannerRejected) as refused:
        model.next(GOAL, GoalHistory())
    assert 'osm_id' in refused.value.reason and 'OpenStreetMap とは ID で結べない' in refused.value.reason


@pytest.mark.parametrize('services,inputs', [(('yuisekin-geosparql',), ()), ((), ('wards',))])
def test_the_id_may_come_from_a_declared_service_or_an_input(services, inputs):
    model, _ = planner(reply('東京23区の名前、relation_id、2020年国勢調査人口の一覧', services=services, inputs=inputs))
    intent = model.next(GOAL, LISTED if inputs else GoalHistory())
    assert 'relation_id' in intent.text


def test_a_key_another_declared_dataset_has_is_not_refused():
    # ekidata lacks code5, jp-admin has it: joined, the code5 is there.
    model, _ = planner(reply('東京23区の区ごとに、code5 と区の中にある ekidata-jp の駅の数を求める',
                             datasets=('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp')))
    assert 'code5' in model.next(GOAL, GoalHistory()).text


def test_codes_neither_the_goal_nor_the_history_gave_are_refused():
    # stage1_c15bbe1, Goal 9: 「市区町村コード（130101〜131100）」 does not exist.
    model, _ = planner(reply('東京23区の市区町村コード（130101〜131100）の面を1つの範囲として結合する'))
    with pytest.raises(PlannerRejected) as refused:
        model.next(GOAL, GoalHistory())
    assert '130101' in refused.value.reason and '131100' in refused.value.reason


def test_a_number_from_the_goal_or_the_history_may_be_written():
    model, _ = planner(reply('relation_id 1761717 の港区の2020年人口を求める', inputs=('wards',)))
    assert '1761717' in model.next(GOAL, LISTED).text
    model, _ = planner(reply('人口 10000 人あたりの駅の数を求める'))
    assert '10000' in model.next(GOAL + '（10000人あたり）', GoalHistory()).text
