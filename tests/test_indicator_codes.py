"""An indicator code of the World Bank's WDI that the data does not have is refused before anything runs.

The small tasks of GeoAI-master-skills (2026-10-14), task 14: the Planner and the Generator wrote the land area as
EN.LND.TOTL.K2 and the density as SP.POP.DNST from memory. The WDI calls them AG.LND.TOTL.K2 and EN.POP.DNST. The
filter matched no row, the code reported the land area of Japan as missing, and the Goal ended without an answer.
"""
from geo_voyager.indicator_codes import INDICATORS, unknown_indicators

WDI = 'yuiseki/worldbank-wdi'


def test_the_codes_are_the_pinned_series_table_one_per_line():
    assert len(INDICATORS) == 1441
    assert INDICATORS['SP.POP.TOTL'] == 'Population, total'
    assert INDICATORS['AG.LND.TOTL.K2'] == 'Land area (sq. km)'


def test_a_code_the_wdi_has_passes():
    assert unknown_indicators('人口（SP.POP.TOTL）と陸地面積（AG.LND.TOTL.K2）') == []


def test_a_code_written_from_memory_is_named_with_the_codes_close_to_it_and_their_names():
    found = unknown_indicators("indicator_code IN ('SP.POP.TOTL', 'EN.LND.TOTL.K2', 'SP.POP.DNST')")
    assert [code for code, _ in found] == ['EN.LND.TOTL.K2', 'SP.POP.DNST']
    close = dict(found)
    assert ('AG.LND.TOTL.K2', 'Land area (sq. km)') in close['EN.LND.TOTL.K2']
    assert 'EN.POP.DNST' in {code for code, _ in close['SP.POP.DNST']}


def test_what_only_looks_like_a_code_is_not_one():
    assert unknown_indicators('EPSG:6933 で面積を測り、ISO_A3 と ISO_A3_EH を比べる。version 1.5.6、ST_Area') == []


def test_the_planner_refuses_an_intent_on_the_wdi_with_a_code_it_does_not_have():
    import pytest
    from geo_voyager.goal_history import GoalHistory
    from geo_voyager.planner import Planner, PlannerRejected
    from unittest.mock import Mock
    client = Mock()
    client.generate.return_value = ('調査項目: 2020 年の国ごとの人口（SP.POP.TOTL）と陸地面積（EN.LND.TOTL.K2）を求める。\n'
                                    '結果名: density\n入力: []\n利用データセット:\n  - yuiseki/worldbank-wdi\n利用サービス: []')
    with pytest.raises(PlannerRejected) as rejected:
        Planner(client).next('世界銀行の国の 2020 年の人口密度を求める', GoalHistory())
    assert 'EN.LND.TOTL.K2' in str(rejected.value) and 'AG.LND.TOTL.K2' in str(rejected.value)


def test_the_generator_refuses_code_on_the_wdi_with_a_code_it_does_not_have():
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import contract_problems
    code = ('from geo_voyager.control_primitives import connect_duckdb, read_table\n\n\n'
            'def density():\n    """Density."""\n    with connect_duckdb() as connection:\n'
            '        data = read_table(connection, "yuiseki/worldbank-wdi", "data")\n'
            '        return data.filter("indicator_code = \'SP.POP.DNST\' AND year = 2020").fetchall()\n')
    problems = contract_problems(Intent('2020 年の国ごとの人口密度', dataset_ids=(WDI,)), code)
    assert any('SP.POP.DNST' in problem and 'EN.POP.DNST' in problem for problem, _ in problems)
