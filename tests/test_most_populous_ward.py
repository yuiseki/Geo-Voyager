from unittest.mock import Mock

from scripts.most_populous_ward import analyze


def test_analysis_selects_one_ward_by_descending_population_through_gateway():
    con = Mock()
    con.execute.return_value.fetchone.return_value = ('13112', '世田谷区', 943664)
    assert analyze(con, 'yuiseki/jp-admin-2026-09') == '東京都23区で人口が最も多い区は世田谷区で、人口は943664人である'
    sql, parameters = con.execute.call_args.args
    assert "BETWEEN '13101' AND '13123'" in sql
    assert 'ORDER BY population DESC' in sql and 'LIMIT 1' in sql
    assert parameters == ['http://gateway:8000/datasets/yuiseki/jp-admin-2026-09']
