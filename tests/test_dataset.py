import pytest

from geo_voyager.dataset import Dataset


def test_dataset_rejects_empty_id():
    with pytest.raises(ValueError):
        Dataset(
            id="",
            description="テスト用メタデータ",
            url="https://example.com/dataset",
            license="CC-BY-4.0",
            formats=("GeoParquet",),
            spatial_coverage="日本",
            temporal_coverage="2020",
            contents=("行政区域",),
        )
