import pytest

from geo_voyager.control_primitives import dataset_url
from geo_voyager.datasets import load_dataset_graph


def test_station_dataset_has_pinned_download_url():
    assert load_dataset_graph().get('yuiseki/ekidata-jp').data_url == (
        'https://huggingface.co/datasets/yuiseki/ekidata-jp/resolve/'
        'a33321099406b47338be0d03a4887059473fde0c/'
        'parquet/2026-10-05/station.2026-07-31.parquet'
    )


def test_dataset_url_supports_only_registered_downloads():
    assert dataset_url('yuiseki/ekidata-jp') == 'http://gateway:8000/datasets/yuiseki/ekidata-jp'
    with pytest.raises(ValueError):
        dataset_url('yuiseki/unregistered')
