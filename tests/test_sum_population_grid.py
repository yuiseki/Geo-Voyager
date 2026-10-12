from unittest.mock import Mock

import duckdb
import numpy
import pytest
import rasterio
from rasterio.transform import from_origin

from geo_voyager.control_primitives import dataset_url, sum_population_grid
from geo_voyager.datasets import load_dataset_graph, load_readable_dataset_graph

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'
ADMIN = 'yuiseki/jp-admin-2026-09'
NODATA = -99999.0


def test_worldpop_dataset_reads_the_pinned_100m_2020_total_population_cog():
    assert load_dataset_graph().get(WORLDPOP).data_url == (
        'https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01/resolve/'
        'cb54e5985662c617a235278bc3529cc172e6368c/'
        'cog/GIS/Population/Global_2015_2030/R2025A/2020/JPN/v1/100m/constrained/'
        'jpn_pop_2020_CN_100m_R2025A_v1.tif'
    )
    assert WORLDPOP in {dataset.id for dataset in load_readable_dataset_graph().all()}
    assert dataset_url(WORLDPOP) == f'http://gateway:8000/datasets/{WORLDPOP}'


def test_worldpop_description_says_which_file_is_readable():
    description = load_dataset_graph().get(WORLDPOP).description
    assert '2020' in description and '100m' in description and 'sum_population_grid' in description


@pytest.fixture
def fixed_data(tmp_path, monkeypatch):
    """A 4 x 2 grid of 0.1 degree pixels and two units, each covering two columns. One pixel is missing."""
    raster = tmp_path / 'pop.tif'
    values = numpy.array([[1, 2, 10, 20], [NODATA, 4, 30, 40]], dtype='float32')
    with rasterio.open(raster, 'w', driver='GTiff', width=4, height=2, count=1, dtype='float32', crs='EPSG:4326',
                       transform=from_origin(139.0, 36.0, 0.1, 0.1), nodata=NODATA) as dst:
        dst.write(values, 1)
    admin = tmp_path / 'municipalities.parquet'
    connection = duckdb.connect()
    connection.execute('LOAD spatial')
    connection.execute(f"""COPY (SELECT * FROM (VALUES
        ('13101', '千代田区', 'POLYGON((139.0 35.8, 139.2 35.8, 139.2 36.0, 139.0 36.0, 139.0 35.8))'),
        ('13102', '中央区', 'POLYGON((139.2 35.8, 139.4 35.8, 139.4 36.0, 139.2 36.0, 139.2 35.8))'),
        ('01100', '札幌市', 'POLYGON((139.0 35.8, 139.4 35.8, 139.4 36.0, 139.0 36.0, 139.0 35.8))'))
        AS t(code5, name, wkt)) TO '{admin}' (FORMAT parquet)""")
    connection.execute(f"""COPY (SELECT code5, name, ST_GeomFromText(wkt) AS geometry FROM '{admin}')
        TO '{tmp_path / "admin.parquet"}' (FORMAT parquet)""")
    paths = {WORLDPOP: str(raster), ADMIN: str(tmp_path / 'admin.parquet')}
    monkeypatch.setattr('geo_voyager.control_primitives.population_grid.dataset_url', paths.__getitem__)
    yield connection
    connection.close()


def test_sums_the_pixels_whose_centre_is_in_each_ward_and_skips_missing_ones(fixed_data):
    rows = sum_population_grid(WORLDPOP, fixed_data, area='東京都23区').order('code5').fetchall()
    assert rows == [('13101', '千代田区', 7.0), ('13102', '中央区', 100.0)]


def test_the_result_is_a_relation_with_named_columns(fixed_data):
    relation = sum_population_grid(WORLDPOP, fixed_data, area='東京都23区')
    assert relation.columns == ['code5', 'name', 'estimated_population']
    assert relation.aggregate('sum(estimated_population)').fetchone()[0] == 107.0


def test_a_missing_value_read_as_none_by_a_foreign_gdal_is_still_skipped(fixed_data, monkeypatch):
    """With another GDAL's data files on the path, rasterio reported nodata as None and summed -99999 as people."""
    real_open = rasterio.open

    class NoNodata:
        def __init__(self, path):
            self.source = real_open(path)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.source.close()

        def __getattr__(self, name):
            return None if name == 'nodata' else getattr(self.source, name)

    monkeypatch.setattr('rasterio.open', NoNodata)
    rows = sum_population_grid(WORLDPOP, fixed_data, area='東京都23区').order('code5').fetchall()
    assert rows[0] == ('13101', '千代田区', 7.0)


@pytest.mark.parametrize('dataset_id', [ADMIN, 'yuiseki/ekidata-jp', 'https://example.com/pop.tif'])
def test_rejects_other_datasets_before_reading(dataset_id):
    connection = Mock()
    with pytest.raises(ValueError):
        sum_population_grid(dataset_id, connection, area='東京都23区')
    connection.read_parquet.assert_not_called()


@pytest.mark.parametrize('area', [None, '東京都', '大阪市'])
def test_rejects_areas_other_than_the_23_wards_before_reading(area):
    connection = Mock()
    with pytest.raises(ValueError):
        sum_population_grid(WORLDPOP, connection, area=area)
    connection.read_parquet.assert_not_called()


def test_the_code_generation_prompts_name_the_primitive():
    from geo_voyager.contracts import PRIMITIVE_CONTRACT
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
    assert 'sum_population_grid(dataset_id, connection, area="東京都23区")' in PRIMITIVE_CONTRACT
    client = Mock()
    client.generate.return_value = '説明:\nx\n---\nコード:\n```python\ndef f():\n    return 1\n```'
    try:
        SkillCandidateGenerator(client).generate(Intent('東京23区の区ごとの推計人口', dataset_ids=(WORLDPOP,)))
    except Exception:
        pass
    prompt = client.generate.call_args.args[0]
    assert '人口格子 Dataset には sum_population_grid を使う' in prompt
