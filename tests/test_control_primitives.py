from unittest.mock import Mock, patch

import pytest

from geo_voyager.control_primitives import connect_duckdb, dataset_url, load_admin_units


def test_connect_duckdb_loads_local_extensions_without_install():
    duckdb = Mock()
    with patch.dict('sys.modules', {'duckdb': duckdb}):
        connection = connect_duckdb()
    settings = duckdb.connect.call_args.kwargs['config']
    assert settings['extension_directory'] == '/opt/duckdb/extensions'
    assert settings['autoinstall_known_extensions'] == 'false'
    assert settings['autoload_known_extensions'] == 'false'
    assert 'allow_unsigned_extensions' not in settings
    assert [call.args for call in connection.execute.call_args_list] == [('LOAD httpfs',), ('LOAD spatial',)]


def test_dataset_url_resolves_only_the_supported_dataset_to_gateway():
    assert dataset_url('yuiseki/jp-admin-2026-09') == 'http://gateway:8000/datasets/yuiseki/jp-admin-2026-09'
    with pytest.raises(ValueError):
        dataset_url('https://other.example/file.parquet')


def test_load_admin_units_returns_relation_without_population_analysis():
    connection = Mock()
    relation = load_admin_units('yuiseki/jp-admin-2026-09', connection)
    connection.read_parquet.assert_called_once_with(dataset_url('yuiseki/jp-admin-2026-09'))
    assert relation is connection.read_parquet.return_value.project.return_value
    connection.read_parquet.return_value.project.assert_called_once_with('code5, name, population')
    relation.filter.assert_not_called()
    relation.order.assert_not_called()
