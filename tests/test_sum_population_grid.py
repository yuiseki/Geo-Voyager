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


def test_the_generator_is_told_the_limit_of_zones_the_primitive_has():
    # The limit was raised to 2,000 for the 1,741 municipalities of Japan, and the prompt still said 100.
    from geo_voyager.control_primitives.population_grid import MAX_ZONES
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
    client = Mock()
    client.generate.return_value = '説明:\nx\n---\nコード:\n```python\ndef f():\n    return 1\n```'
    try:
        SkillCandidateGenerator(client).generate(Intent('市区町村ごとの推計人口', dataset_ids=(WORLDPOP,)))
    except Exception:
        pass
    prompt = client.generate.call_args.args[0]
    assert f'一度に{MAX_ZONES:,}区域まで' in prompt and '一度に100区域まで' not in prompt


def test_the_grid_is_fetched_once_to_the_sandboxs_tmp_and_read_there(tmp_path, monkeypatch):
    # Read by Range through the Gateway, 1,000 circles of 1 km took 166 s (0.17 s a zone); fetched whole (131 MB,
    # 17 s) and read from /tmp, the 8,766 stations' circles took 6.8 s (measured in the sandbox, 2026-10-15).
    import io
    from geo_voyager.control_primitives import population_grid
    small_grid(tmp_path / 'source.tif')
    fetched = []

    def urlopen(url, timeout):
        fetched.append(url)
        return io.BytesIO((tmp_path / 'source.tif').read_bytes())

    monkeypatch.setattr(population_grid, 'urlopen', urlopen)
    monkeypatch.setattr(population_grid, 'LOCAL_GRID', tmp_path / 'grid.tif')
    url = 'http://gateway:8000/datasets/yuiseki/worldpop-jp-2026-01'
    assert population_grid.local_grid(url) == tmp_path / 'grid.tif'
    assert population_grid.local_grid(url) == tmp_path / 'grid.tif'
    assert fetched == [url]                                            # once
    assert (tmp_path / 'grid.tif').read_bytes() == (tmp_path / 'source.tif').read_bytes()


def test_the_limit_of_zones_holds_the_stations_of_japan():
    from geo_voyager.control_primitives.population_grid import MAX_ZONES
    assert MAX_ZONES >= 9281                                           # the operating stations' circles, one a station


def test_a_zone_of_parts_far_apart_is_summed_part_by_part(tmp_path, monkeypatch):
    # The 1,741 municipalities went over the sandbox's 1 GB: a municipality of islands far apart (Ogasawara spans
    # some 17 by 7 degrees) was cut from the grid as one window of its whole extent. Each part is cut on its own.
    import duckdb
    from geo_voyager.control_primitives import population_grid
    small_grid(tmp_path / 'grid.tif')
    monkeypatch.setattr(population_grid, 'dataset_url', lambda dataset_id: str(tmp_path / 'grid.tif'))
    windows = []
    real_mask = population_grid.rasterio_mask

    def mask(source, shapes, **kwargs):
        windows.append(shapes)
        return real_mask(source, shapes, **kwargs)

    monkeypatch.setattr(population_grid, 'rasterio_mask', mask)
    connection = duckdb.connect()
    connection.execute('INSTALL spatial; LOAD spatial')
    zones = connection.sql("SELECT 'islands' AS name, ST_GeomFromText('MULTIPOLYGON(((139.0 35.98, 139.01 35.98, 139.01 36.0, "
                           "139.0 36.0, 139.0 35.98)), ((139.03 35.96, 139.04 35.96, 139.04 35.97, 139.03 35.97, 139.03 35.96)))') AS geometry")
    sums = population_grid.sum_population_grid(connection, zones)
    assert sums.fetchall() == [('islands', 2.0)]                        # 1 of the first part's 2 is missing; 1 in the second
    assert len(windows) == 2 and all(len(shapes) == 1 and shapes[0]['type'] == 'Polygon' for shapes in windows)


def test_a_zone_wholly_outside_the_grid_is_an_error_not_no_one(tmp_path, monkeypatch):
    import duckdb
    import pytest
    from geo_voyager.control_primitives import population_grid
    small_grid(tmp_path / 'grid.tif')
    monkeypatch.setattr(population_grid, 'dataset_url', lambda dataset_id: str(tmp_path / 'grid.tif'))
    connection = duckdb.connect()
    connection.execute('INSTALL spatial; LOAD spatial')
    zones = connection.sql("SELECT 'sea' AS name, ST_GeomFromText('POLYGON((150 20, 151 20, 151 21, 150 21, 150 20))') AS geometry")
    with pytest.raises(ValueError, match='outside the grid'):
        population_grid.sum_population_grid(connection, zones)


def test_a_zone_without_a_geometry_is_named(tmp_path, monkeypatch):
    # GeoAI-skills' small task 11 (2026-10-15): a zone with a NULL geometry (jp-admin has 9 municipalities without a
    # face) failed inside the primitive as "the JSON object must be str ... not NoneType", twice.
    import duckdb
    import pytest
    from geo_voyager.control_primitives import population_grid
    small_grid(tmp_path / 'grid.tif')
    monkeypatch.setattr(population_grid, 'dataset_url', lambda dataset_id: str(tmp_path / 'grid.tif'))
    connection = duckdb.connect()
    connection.execute('INSTALL spatial; LOAD spatial')
    zones = connection.sql("SELECT '歯舞群島' AS name, NULL::GEOMETRY AS geometry")
    with pytest.raises(ValueError, match='no geometry.*geometry IS NOT NULL'):
        population_grid.sum_population_grid(connection, zones)
