from unittest.mock import Mock

import pytest

from geo_voyager.curriculum import Curriculum, CurriculumRejected, ProposedGoal


def curriculum(reply):
    client = Mock(); client.generate.return_value = reply
    return Curriculum(client), client


FINDING = {'goal': '渋谷区のカフェの数', 'answer': '{"tag": "amenity=cafe", "count": 459}',
           'steps': [], 'resources': ['overpass'], 'targets': [{'name': '渋谷区', 'id_type': 'relation_id', 'id_value': '1759477'}]}
ATTEMPT = {'goal': '23区で最も人口の多い区', 'success': False, 'stop_reason': 'final_critic_failed',
           'reason': 'CRITIC_SECRET 答えの根拠が無い',
           'checked_failures': [{'step': 2, 'intent': '区の中心点', 'resources': ['overpass'], 'kind': 'execution_error',
                                 'line': 'AssertionError: no center in element', 'critic_reason': 'CRITIC_SECRET'}]}


def test_the_curriculum_proposes_one_goal_with_its_reason():
    agent, client = curriculum('Goal: 新宿区の amenity=cafe の数を求める\n理由: 渋谷区と比べる材料にする\n予想: 約 400 件')
    proposed = agent.propose([FINDING], [ATTEMPT])
    assert proposed == ProposedGoal('新宿区の amenity=cafe の数を求める', '渋谷区と比べる材料にする', '約 400 件')
    prompt = client.generate.call_args.args[0]
    for text in ('渋谷区のカフェの数', '"count": 459', '渋谷区 (relation_id=1759477)', '23区で最も人口の多い区',
                 '未達（モデルを使わずに確かめた失敗: overpass で実行のエラー）', 'Service overpass', 'Dataset yuiseki/jp-admin-2026-09', '少しずつ難しく', 'まだ分かっていない'):
        assert text in prompt
    # A Critic's reason, and how the Goal stopped (which a Critic can decide), do not reach the curriculum (ADR 0011).
    assert 'CRITIC_SECRET' not in prompt and 'final_critic_failed' not in prompt


def test_the_prompt_starts_from_nothing_when_nothing_is_known():
    agent, client = curriculum('Goal: 東京23区の区の数を求める\n理由: 最初の足場\n予想: 23')
    agent.propose([], [])
    assert 'まだ何も分かっていない' in client.generate.call_args.args[0]


def test_only_the_latest_findings_and_attempts_are_shown():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    findings = [dict(FINDING, goal=f'goal {n}') for n in range(50)]
    agent.propose(findings, [dict(ATTEMPT, goal=f'attempt {n}') for n in range(50)])
    prompt = client.generate.call_args.args[0]
    assert 'goal 49' in prompt and 'goal 0\n' not in prompt and 'goal 10\n' not in prompt
    assert 'attempt 49' in prompt and 'attempt 10\n' not in prompt


@pytest.mark.parametrize('reply', [
    '', '新宿区のカフェの数', 'Goal: \n理由: y', 'Goal: x を求める', 'Goal: a\nGoal: b\n理由: y',
    'Goal: 渋谷区のカフェの数\n理由: もう一度',
    'Goal: /api/interpreter で渋谷区のカフェを数える\n理由: y\n予想: 3',
    'Goal: 新宿区のカフェの数\n理由: y', 'Goal: 新宿区のカフェの数\n理由: y\n予想: ',
])
def test_an_unusable_or_repeated_goal_is_rejected(reply):
    agent, _ = curriculum(reply)
    with pytest.raises(CurriculumRejected):
        agent.propose([FINDING], [])


def test_a_rejection_note_is_shown_on_the_next_call():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([], [], note='前回の応答は使えなかった: Goal: の行が無い')
    assert '前回の応答は使えなかった: Goal: の行が無い' in client.generate.call_args.args[0]


def test_the_prompt_counts_how_often_each_resource_was_used_and_names_the_unused_ones():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([FINDING, dict(FINDING, goal='b', resources=['overpass', 'yuisekin-geosparql'])], [])
    prompt = client.generate.call_args.args[0]
    assert 'overpass: 2 件' in prompt and 'yuisekin-geosparql: 1 件' in prompt
    unused = prompt.split('まだ使っていないリソース:', 1)[1].split('\n', 1)[0]
    for resource in ('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp', 'nominatim', 'valhalla', 'taginfo'):
        assert resource in unused
    assert 'overpass' not in unused


def test_a_dataset_the_sandbox_can_not_read_is_neither_shown_nor_suggested():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([FINDING], [])
    prompt = client.generate.call_args.args[0]
    for dataset in ('yuiseki/mlit-toshi-keikaku-jp', 'yuiseki/osm-japan-src-2026-08'):
        assert dataset not in prompt, dataset


def test_the_prompt_asks_for_questions_about_the_world_not_about_identifiers_and_for_a_new_kind_of_question():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([FINDING], [])
    prompt = client.generate.call_args.args[0]
    for text in ('識別子', '何を表すか', '同じ型の問い', 'まだ使っていないリソース'):
        assert text in prompt


def test_the_history_shown_stays_within_a_length_budget_newest_first():
    from geo_voyager.curriculum import HISTORY_CHARS
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
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


def test_the_world_to_explore_is_as_wide_as_the_resources():
    # The first resources were Tokyo's (the 23 wards in YuisekinGeoSPARQL, Overpass). The datasets now cover every
    # municipality of Japan and the countries of the world, and a curriculum told to explore Tokyo would not ask of them.
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([], [])
    prompt = client.generate.call_args.args[0]
    assert '東京の世界' not in prompt and '日本と世界' in prompt


class Embedding:
    """Each text's vector is given by the test; the curriculum compares a Goal with the latest tries by cosine."""

    def __init__(self, vectors):
        self.vectors, self.calls = vectors, []

    def embed(self, texts):
        self.calls.append(texts)
        return [self.vectors[text] for text in texts]


def test_a_goal_that_says_again_what_one_of_the_latest_tries_asked_is_rejected_naming_that_try():
    # Exploration 11 (2026-10-15): Goals 18 to 31 asked households per person nine times, reworded, and binned the
    # municipalities' points by longitude, then latitude, then both. The prompt said not to go on with the same kind of
    # question; the model went on. The rewordings were 0.95 or more alike (embeddinggemma) to one of the 5 tries before.
    client = Mock(); client.generate.return_value = 'Goal: 人口千人あたり世帯数が最も高い市区町村\n理由: y\n予想: 3'
    embedding = Embedding({'人口千人あたり世帯数が最も高い市区町村': [1.0, 0.1], '人口1万人あたり世帯数の最大': [1.0, 0.0],
                           '横浜市の駅までの距離': [0.0, 1.0]})
    attempts = [dict(ATTEMPT, goal='人口1万人あたり世帯数の最大'), dict(ATTEMPT, goal='横浜市の駅までの距離')]
    with pytest.raises(CurriculumRejected) as rejected:
        Curriculum(client, embedding=embedding).propose([], attempts)
    assert '人口1万人あたり世帯数の最大' in rejected.value.reason and '横浜市の駅までの距離' not in rejected.value.reason


def test_a_goal_on_another_subject_passes():
    client = Mock(); client.generate.return_value = 'Goal: 新しい問い\n理由: y\n予想: 3'
    embedding = Embedding({'新しい問い': [1.0, 0.0], '横浜市の駅までの距離': [0.0, 1.0]})
    proposed = Curriculum(client, embedding=embedding).propose([], [dict(ATTEMPT, goal='横浜市の駅までの距離')])
    assert proposed.goal == '新しい問い'


def test_a_rewording_of_a_goal_tried_long_before_is_refused_too():
    # Exploration 11, Goals 32 to 61, compared with the 5 tries before each: Goal 46 binned the points again as Goal 30
    # had (0.967), Goal 47 asked households per person again as Goal 23 had (0.975), 16 and 24 Goals later.
    from geo_voyager.curriculum import EMBEDDED_AT_ONCE
    client = Mock(); client.generate.return_value = 'Goal: 世帯数の比の最大\n理由: y\n予想: 3'
    tries = [f'try {n}' for n in range(2 * EMBEDDED_AT_ONCE + 3)]
    embedding = Embedding({'世帯数の比の最大': [1.0, 0.0], '人口あたり世帯数の最大': [1.0, 0.05]}
                          | {text: [0.0, 1.0] for text in tries})
    attempts = [dict(ATTEMPT, goal='人口あたり世帯数の最大')] + [dict(ATTEMPT, goal=text) for text in tries]
    with pytest.raises(CurriculumRejected) as rejected:
        Curriculum(client, embedding=embedding).propose([], attempts)
    assert '人口あたり世帯数の最大' in rejected.value.reason
    assert all(len(call) <= EMBEDDED_AT_ONCE for call in embedding.calls)


FOUND = dict(FINDING, prediction='約 200 件', surprise=0.36)


def test_the_curriculum_predicts_the_main_value_of_its_goal_before_it_is_explored():
    agent, client = curriculum('Goal: 新宿区の amenity=cafe の数を求める\n理由: y\n予想: 約 400 件')
    assert agent.propose([], []).prediction == '約 400 件'
    prompt = client.generate.call_args.args[0]
    assert '予想:' in prompt and '本気の見積もり' in prompt


def test_each_finding_is_shown_with_what_was_predicted_and_how_far_off_it_was():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([FOUND], [])
    prompt = client.generate.call_args.args[0]
    assert '予想: 約 200 件 → 外れ度 0.36' in prompt


def test_the_findings_whose_predictions_failed_most_are_shown_however_old():
    # The reward: where a prediction failed, the world is not as the curriculum thought, and there is more to learn.
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    findings = ([dict(FOUND, goal='old surprise', surprise=0.9)] +
                [dict(FOUND, goal=f'goal {n}', surprise=0.0) for n in range(40)])
    agent.propose(findings, [])
    prompt = client.generate.call_args.args[0]
    surprising = prompt[prompt.index('予想が大きく外れた発見'):prompt.index('これまでの発見:')]
    assert 'old surprise' in surprising and '外れ度 0.90' in surprising
    assert '掘り下げ' in prompt


def test_a_finding_explored_before_predictions_is_shown_without_one():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    agent.propose([FINDING], [])
    assert '外れ度' not in client.generate.call_args.args[0].split('これまでの発見:', 1)[1]


def drawn():
    from geo_voyager.ingredients import Ingredients
    return Ingredients(('amenity=place_of_worship', 'leisure=pitch', 'shop=bakery'), ('足立区', '港区'),
                       ('周りの推計人口', '公示地価'), ('SP.POP.TOTL',))


def test_on_exploration_the_drawn_ingredients_are_shown_and_the_goal_names_those_it_used():
    agent, client = curriculum('Goal: 足立区で、周りの推計人口が最も多い寺社はどこか\n理由: y\n予想: 西新井大師\n'
                               '材料: amenity=place_of_worship、足立区、周りの推計人口')
    proposed = agent.propose([], [], ingredients=drawn())
    assert proposed.ingredients == ('amenity=place_of_worship', '足立区', '周りの推計人口')
    prompt = client.generate.call_args.args[0]
    assert '今回の材料' in prompt and 'shop=bakery' in prompt and '材料:' in prompt


@pytest.mark.parametrize('line', ['', '材料: ', '材料: amenity=cafe', '材料: 渋谷区、公示地価、amenity=cafe'])
def test_on_exploration_a_goal_that_names_no_drawn_ingredient_or_one_not_drawn_is_refused(line):
    agent, _ = curriculum(f'Goal: x を求める\n理由: y\n予想: 3\n{line}')
    with pytest.raises(CurriculumRejected):
        agent.propose([], [], ingredients=drawn())


def test_on_exploration_an_ingredient_written_with_its_description_is_read_by_its_name():
    # Explore 31: the curriculum copied 件数（範囲の中にある数） and 区の人口（…（2020 年国勢調査、…）） from the list of
    # ingredients, and was refused three times for naming ingredients not drawn.
    agent, _ = curriculum('Goal: 足立区で、周りの推計人口が最も多い寺社はどこか\n理由: y\n予想: 西新井大師\n'
                          '材料: amenity=place_of_worship（23 区で 1 件、うち面 0 件。A place）、足立区、'
                          '周りの推計人口（周り（たとえば半径 1 km）に住む推計人口（WorldPop の 100 m 格子））')
    assert agent.propose([], [], ingredients=drawn()).ingredients == ('amenity=place_of_worship', '足立区', '周りの推計人口')


def test_when_nothing_is_drawn_the_curriculum_digs_and_no_ingredient_is_asked_for():
    agent, client = curriculum('Goal: x を求める\n理由: y\n予想: 3')
    assert agent.propose([], []).ingredients == ()
    assert '今回の材料' not in client.generate.call_args.args[0]


def test_the_example_of_a_drawn_question_is_not_a_task_held_for_evaluation():
    # GeoAI-master-skills' small task 27 asks for the most expensive tennis court of Tokyo; it is not shown as the example.
    agent, client = curriculum('Goal: x\n理由: y\n予想: 3\n材料: 港区')
    agent.propose([], [], ingredients=drawn())
    prompt = client.generate.call_args.args[0]
    assert 'テニスコート' not in prompt


def photo(areas=('墨田区', '台東区')):
    from geo_voyager.ingredients import Ingredients
    return Ingredients(('shop=photo', 'waterway=weir', 'landuse=vineyard'), areas, ('面積', '件数'), ('SP.POP.TOTL',))


def test_on_exploration_a_goal_on_the_areas_of_a_kind_the_named_wards_have_none_of_is_refused():
    # Explore 34: shown 墨田区 5 件（面 0）、台東区 3 件（面 0）, the curriculum asked the total area of shop=photo there;
    # the answer 0 was right, and the Critic failed it until the time ran out.
    agent, _ = curriculum('Goal: 墨田区と台東区で、OSMの面として記録された shop=photo の総面積はどれほどか\n理由: y\n予想: 約 500 m²\n'
                          '材料: shop=photo、墨田区、台東区、面積')
    with pytest.raises(CurriculumRejected, match='shop=photo の面は 墨田区 0 件、台東区 0 件'):
        agent.propose([], [], ingredients=photo())


def test_on_exploration_the_points_of_such_a_kind_or_the_areas_where_a_ward_has_some_may_be_asked():
    agent, _ = curriculum('Goal: 墨田区と台東区で、shop=photo の件数が多いのはどちらか\n理由: y\n予想: 墨田区\n'
                          '材料: shop=photo、墨田区、台東区、件数')
    assert agent.propose([], [], ingredients=photo()).ingredients == ('shop=photo', '墨田区', '台東区', '件数')
    agent, _ = curriculum('Goal: 墨田区と板橋区で、shop=photo の面の総面積はどれほどか\n理由: y\n予想: 約 500 m²\n'
                          '材料: shop=photo、墨田区、板橋区、面積')
    assert agent.propose([], [], ingredients=photo(('墨田区', '板橋区'))).ingredients == ('shop=photo', '墨田区', '板橋区', '面積')


def test_on_exploration_a_goal_on_a_kind_the_named_wards_have_none_of_is_refused():
    # Explore 36: shown 港区 0 件、中央区 0 件, the curriculum asked the sum of the distances of
    # man_made=communications_tower there to their stations, and predicted 0 km.
    from geo_voyager.ingredients import Ingredients
    towers = Ingredients(('man_made=communications_tower', 'waterway=weir', 'landuse=vineyard'), ('港区', '中央区'),
                         ('駅までの直線距離', '件数'), ('SP.POP.TOTL',))
    agent, _ = curriculum('Goal: 港区と中央区で、man_made=communications_tower の各地点から最寄りの運行中の駅までの直線距離の合計は何kmか\n'
                          '理由: y\n予想: 0 km\n材料: man_made=communications_tower、港区、中央区、駅までの直線距離')
    with pytest.raises(CurriculumRejected, match='man_made=communications_tower は 港区 0 件、中央区 0 件'):
        agent.propose([], [], ingredients=towers)
