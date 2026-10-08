import pytest

from geo_voyager.dataset import Dataset
from geo_voyager.dataset_graph import DatasetGraph


@pytest.fixture
def dataset():
    return Dataset(
        id="example/test",
        description="テスト用メタデータ",
        url="https://example.com/dataset",
        license="CC-BY-4.0",
        formats=("GeoParquet",),
        spatial_coverage="日本",
        temporal_coverage="2020",
        contents=("行政区域",),
    )


def test_graph_registers_dataset(dataset):
    graph = DatasetGraph()

    graph.register(dataset)

    assert graph.all() == [dataset]


def test_graph_gets_dataset_by_id(dataset):
    graph = DatasetGraph()
    graph.register(dataset)

    assert graph.get(dataset.id) == dataset


def test_graph_rejects_unknown_id():
    with pytest.raises(KeyError, match="unknown/dataset"):
        DatasetGraph().get("unknown/dataset")
