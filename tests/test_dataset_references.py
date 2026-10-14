"""What the Planner is told about a dataset comes from its reference in GeoAI-skills (measured facts: what a row is,
its ids, the keys it does not have, what the columns mean), cut down to the columns the sandbox's primitive returns."""
from unittest.mock import Mock

from geo_voyager.dataset_references import SOURCE, planner_text
from geo_voyager.datasets import load_readable_dataset_graph
from geo_voyager.goal_history import GoalHistory
from geo_voyager.planner import Planner


def test_the_references_say_which_commit_of_geoai_skills_they_were_copied_from():
    assert SOURCE['repository'] == 'https://github.com/yuiseki/GeoAI-skills' and len(SOURCE['commit']) == 40


def test_every_dataset_the_sandbox_can_read_has_a_reference():
    for dataset in load_readable_dataset_graph().all():
        assert planner_text(dataset.id)


def test_the_boundaries_say_what_a_row_is_the_key_they_lack_and_what_population_means():
    text = planner_text('yuiseki/jp-admin-2026-09')
    assert '1 行は' in text and '市区町村' in text
    assert 'osm_id' in text and 'OpenStreetMap とは ID で結べない' in text           # the relation_id the Planner asked for
    assert 'population（2020 年国勢調査の人口' in text
    assert '東京23区の23区は1回で読める' in text                                         # what the primitive adds


def test_the_stations_are_described_under_the_references_names_which_read_table_keeps():
    text = planner_text('yuiseki/ekidata-jp')
    assert 'e_status（0 が運行中' in text
    assert '乗換駅は路線の数だけ行がある' in text and 'code5' in text                   # no municipal code: join in space


def test_the_estimate_says_it_is_one_and_that_the_census_is_read_otherwise():
    text = planner_text('yuiseki/worldpop-jp-2026-01')
    assert '国勢調査ではなく推計' in text and 'sum_population_grid' in text
    assert 'Goal が WorldPop・推計を名指ししない人口は、yuiseki/jp-admin-2026-09 の国勢調査人口を使う' in text


def test_the_planner_is_shown_these_texts_and_they_fit_the_context():
    client = Mock(); client.generate.return_value = 'DONE'
    Planner(client).next('東京23区の人口', GoalHistory())
    prompt = client.generate.call_args.args[0]
    texts = [planner_text(dataset.id) for dataset in load_readable_dataset_graph().all()]
    assert all(f'Dataset {dataset.id}: {text}' in prompt for dataset, text in zip(load_readable_dataset_graph().all(), texts))
    assert sum(len(text) for text in texts) < 2500           # the context is 16,384 tokens; the largest prompts are ~26 KB


def test_the_curriculum_is_shown_them_too_and_the_first_plan_route_keeps_the_catalog():
    from geo_voyager.curriculum import Curriculum
    client = Mock(); client.generate.return_value = 'Goal: x\n理由: y'
    try:
        Curriculum(client).propose([], [])
    except Exception:
        pass
    assert planner_text('yuiseki/jp-admin-2026-09') in client.generate.call_args.args[0]
    planned = Mock(); planned.generate.return_value = '調査項目: x\n利用データセット:\n  - yuiseki/jp-admin-2026-09'
    try:
        Planner(planned).plan_goal('東京23区の人口')
    except Exception:
        pass
    assert planner_text('yuiseki/jp-admin-2026-09') not in planned.generate.call_args.args[0]


def test_the_centre_of_a_ward_is_the_representative_point_of_jp_admin_not_an_overpass_centre():
    # a_run4, Goal 5 step 4 and timeout_run1, Goal 8 step 5: the Planner asked Overpass for the centres of two wards and
    # the code asked for the centre of an area element, which has none. The answer is measured from jp-admin's
    # representative points; an OSM relation's centre is another point (世田谷区 35.6365, 139.6345 against 35.6465,
    # 139.6532), so being told only how to get it from Overpass would answer another distance.
    from geo_voyager.planner import Planner
    from geo_voyager.services import load_service_graph
    assert 'rep_lon' in planner_text('yuiseki/jp-admin-2026-09') and 'Overpass で求めない' in planner_text('yuiseki/jp-admin-2026-09')
    overpass = load_service_graph().get('overpass').description
    assert 'area 要素は out center を付けても center を返さない' in overpass
    assert 'yuiseki/jp-admin-2026-09 の rep_lon' in overpass
    plan = Planner(Mock())
    plan.llm_client.generate.return_value = 'DONE'
    from geo_voyager.goal_history import GoalHistory
    plan.next('g', GoalHistory())
    prompt = plan.llm_client.generate.call_args.args[0]
    assert 'Overpass で求めない' in prompt and 'area 要素は out center を付けても center を返さない' in prompt


def test_the_planner_is_told_a_columns_note_on_how_to_use_it_as_the_generator_is():
    # jp-admin's geometry note (take touching pairs with ST_Intersects) reached the Generator's table text only; the
    # Planner, which decides what a step measures, was not told.
    text = planner_text('yuiseki/jp-admin-2026-09')
    assert 'ST_Intersects' in text and 'ST_Touches' in text


def test_a_join_keys_note_reaches_the_planner_and_the_generator():
    # The small tasks of GeoAI-skills (2026-10-14), task 14: the WDI reference says, on country_code, to keep the
    # countries whose Region is not empty; neither the Planner nor the Generator was told, and the run left out the
    # aggregates by matching Natural Earth instead, dropping Kosovo and the Channel Islands without a word.
    from geo_voyager.contracts.tables import table_contract
    for text in (planner_text('yuiseki/worldbank-wdi'), table_contract(('yuiseki/worldbank-wdi',))):
        assert 'countries の Region が空でないものに絞る' in text
    for text in (planner_text('yuiseki/jp-admin-2026-09'), table_contract(('yuiseki/jp-admin-2026-09',))):
        assert '親と区が重なるので ward is null に絞る' in text
