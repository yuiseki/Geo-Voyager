from unittest.mock import Mock

import pytest

from scripts.analyze_tokyo23 import analyze


def test_fixed_analysis_reads_only_gateway_and_returns_integer_population():
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [
        (f"131{ward:02d}", f"区{ward}", 100) for ward in range(1, 24)
    ]
    assert analyze(connection) == (23, 2300)
    sql, parameters = connection.execute.call_args.args
    assert "SELECT code5, name, population" in sql
    assert "BETWEEN '13101' AND '13123'" in sql
    assert parameters == ["http://gateway:8000/datasets/yuiseki/jp-admin-2026-09"]


def test_fixed_analysis_rejects_non_23_rows():
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = []
    with pytest.raises(ValueError, match="23"):
        analyze(connection)


@pytest.mark.parametrize("population", [None, "100", 100.5])
def test_fixed_analysis_rejects_non_integer_population(population):
    connection = Mock()
    connection.execute.return_value.fetchall.return_value = [("13101", "千代田区", population)] * 23
    with pytest.raises(TypeError, match="population"):
        analyze(connection)
