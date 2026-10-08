from unittest.mock import Mock

import pytest

from geo_voyager.control_primitives import dataset_url, load_admin_units, load_stations
from geo_voyager.datasets import load_dataset_graph


def test_station_dataset_has_pinned_download_url():
    assert load_dataset_graph().get('yuiseki/ekidata-jp').data_url == (
        'https://huggingface.co/datasets/yuiseki/ekidata-jp/resolve/'
        'a33321099406b47338be0d03a4887059473fde0c/'
        'parquet/2026-10-05/station.2026-07-31.parquet'
    )


def test_load_stations_reads_gateway_and_normalizes_columns_without_analysis():
    connection = Mock()
    relation = load_stations('yuiseki/ekidata-jp', connection)
    connection.read_parquet.assert_called_once_with('http://gateway:8000/datasets/yuiseki/ekidata-jp')
    raw = connection.read_parquet.return_value
    raw.project.assert_called_once_with('station_name AS name, lat AS latitude, lon AS longitude')
    assert relation is raw.project.return_value
    relation.filter.assert_not_called()
    relation.order.assert_not_called()
    relation.aggregate.assert_not_called()


@pytest.mark.parametrize('dataset_id', ['yuiseki/jp-admin-2026-09', 'https://example.com/stations.parquet'])
def test_load_stations_rejects_other_dataset_before_reading(dataset_id):
    connection = Mock()
    with pytest.raises(ValueError):
        load_stations(dataset_id, connection)
    connection.read_parquet.assert_not_called()


def test_admin_primitive_rejects_station_dataset():
    connection = Mock()
    with pytest.raises(ValueError):
        load_admin_units('yuiseki/ekidata-jp', connection)
    connection.read_parquet.assert_not_called()


def test_dataset_url_supports_only_registered_downloads():
    assert dataset_url('yuiseki/ekidata-jp') == 'http://gateway:8000/datasets/yuiseki/ekidata-jp'
    with pytest.raises(ValueError):
        dataset_url('yuiseki/unregistered')
