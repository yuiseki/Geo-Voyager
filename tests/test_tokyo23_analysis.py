from unittest.mock import Mock, patch

import pytest

from scripts.analyze_tokyo23 import analyze


def test_fixed_analysis_reads_aoi_through_primitive_and_returns_integer_population():
    connection = Mock()
    with patch('scripts.analyze_tokyo23.load_admin_units') as load:
        load.return_value.fetchall.return_value = [
            (f'code{ward}', f'区{ward}', 100) for ward in range(1, 24)
        ]
        assert analyze(connection) == (23, 2300)
    load.assert_called_once_with('yuiseki/jp-admin-2026-09', connection, area='東京都23区')


def test_fixed_analysis_rejects_non_23_rows():
    with patch('scripts.analyze_tokyo23.load_admin_units') as load:
        load.return_value.fetchall.return_value = []
        with pytest.raises(ValueError, match='23'):
            analyze(Mock())


@pytest.mark.parametrize('population', [None, '100', 100.5])
def test_fixed_analysis_rejects_non_integer_population(population):
    with patch('scripts.analyze_tokyo23.load_admin_units') as load:
        load.return_value.fetchall.return_value = [('test-code', 'テスト区', population)] * 23
        with pytest.raises(TypeError, match='population'):
            analyze(Mock())
