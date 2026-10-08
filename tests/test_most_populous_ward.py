from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

from geo_voyager.skills import load_skill_library


def test_population_skill_uses_primitives_and_computes_result_without_hardcoded_ward():
    skill = load_skill_library().get('most_populous_admin_unit')
    relation = Mock()
    relation.filter.return_value.order.return_value.limit.return_value.fetchone.return_value = ('13101', 'テスト区', 123)
    with patch('geo_voyager.control_primitives.connect_duckdb') as connect, \
         patch('geo_voyager.control_primitives.load_admin_units', return_value=relation) as load:
        output = StringIO()
        with redirect_stdout(output):
            exec(skill.code, {'dataset_id': 'yuiseki/jp-admin-2026-09'})
    load.assert_called_once_with('yuiseki/jp-admin-2026-09', connect.return_value.__enter__.return_value)
    relation.filter.assert_called_once_with("code5 BETWEEN '13101' AND '13123'")
    relation.filter.return_value.order.assert_called_once_with('population DESC')
    relation.filter.return_value.order.return_value.limit.assert_called_once_with(1)
    assert output.getvalue() == '東京都23区で人口が最も多い区はテスト区で、人口は123人である\n'
    assert '世田谷' not in skill.code and '943664' not in skill.code
