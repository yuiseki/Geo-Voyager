from unittest.mock import Mock

import pytest

from geo_voyager.control_primitives import dataset_url
from geo_voyager.datasets import load_dataset_graph, load_readable_dataset_graph

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'


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


def test_the_code_generation_prompts_name_the_primitive():
    from geo_voyager.contracts.prompt import PRIMITIVE_CONTRACT
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
    assert 'sum_population_grid(connection, zones)' in PRIMITIVE_CONTRACT
    client = Mock()
    client.generate.return_value = '説明:\nx\n---\nコード:\n```python\ndef f():\n    return 1\n```'
    try:
        SkillCandidateGenerator(client).generate(Intent('東京23区の区ごとの推計人口', dataset_ids=(WORLDPOP,)))
    except Exception:
        pass
    prompt = client.generate.call_args.args[0]
    assert 'sum_population_grid(connection, zones)' in prompt and 'geometry 列を持つ relation' in prompt


def test_the_contract_shows_the_tables_of_the_declared_datasets():
    from geo_voyager.contracts.prompt import primitive_contract
    from geo_voyager.intent import Intent
    text = primitive_contract(Intent('区ごとの駅', ('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp')))
    assert 'read_table(connection, "yuiseki/ekidata-jp", "station")' in text and '東京23区: filter(' in text
    assert 'load_admin_units' not in text and 'load_stations' not in text


def small_grid(path):
    """A 4 x 4 grid of 1 person a pixel, 0.01 degrees a pixel from 139.0 E, 36.0 N, one pixel missing."""
    import numpy
    import rasterio
    from rasterio.transform import from_origin
    values = numpy.ones((4, 4), dtype='float32')
    values[0, 0] = -99999
    with rasterio.open(path, 'w', driver='GTiff', width=4, height=4, count=1, dtype='float32', crs='EPSG:4326',
                       transform=from_origin(139.0, 36.0, 0.01, 0.01), nodata=-99999) as target:
        target.write(values, 1)


def test_zones_with_a_geometry_alone_are_summed_in_their_order(tmp_path, monkeypatch):
    # The small tasks of GeoAI-skills (2026-10-14), task 11: zones of a geometry and no other column made the table
    # of sums "(, estimated_population DOUBLE)", a syntax error the model could not read as its own.
    import duckdb
    from geo_voyager.control_primitives import population_grid
    small_grid(tmp_path / 'grid.tif')
    monkeypatch.setattr(population_grid, 'dataset_url', lambda dataset_id: str(tmp_path / 'grid.tif'))
    connection = duckdb.connect()
    connection.execute('INSTALL spatial; LOAD spatial')
    zones = connection.sql("SELECT ST_GeomFromText(wkt) AS geometry FROM (VALUES "
                           "('POLYGON((139.0 35.98, 139.02 35.98, 139.02 36.0, 139.0 36.0, 139.0 35.98))'), "
                           "('POLYGON((139.0 35.96, 139.04 35.96, 139.04 35.98, 139.0 35.98, 139.0 35.96))')) t(wkt)")
    sums = population_grid.sum_population_grid(connection, zones)
    assert sums.columns == ['estimated_population']
    assert [row[0] for row in sums.fetchall()] == [3.0, 8.0]          # the missing pixel is no one
