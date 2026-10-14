"""read_table returns tables with a geometry, so a step joins them in space (a station in a ward) with
DuckDB instead of a primitive made for each question.

The data here is small and fixed, written in the forms of the real files: the boundaries carry the JGD2000 label
(EPSG:4612) of jp-admin-2026-09, the stations are GeoParquet in OGC:CRS84 as in ekidata-jp, and the grid is a
WorldPop-like GeoTIFF with -99999 for a missing pixel.
"""
import sys
from unittest.mock import Mock

import duckdb
import numpy
import pytest
import rasterio
from rasterio.transform import from_origin

from geo_voyager.control_primitives import read_table, sum_population_grid

# rasterio multiplies an Affine with `*`, which affine 3 warns about; -W error must not turn their warning into ours.
pytestmark = pytest.mark.filterwarnings("ignore:Use `@` matmul instead of `\\*` mul operator:PendingDeprecationWarning")

ADMIN = 'yuiseki/jp-admin-2026-09'
STATIONS = 'yuiseki/ekidata-jp'
WORLDPOP = 'yuiseki/worldpop-jp-2026-01'
NODATA = -99999.0


def wards(connection):
    return read_table(connection, ADMIN, 'municipalities').filter("pref_code = '13' AND name LIKE '%区'")


@pytest.fixture
def connection(tmp_path, monkeypatch):
    """Two wards side by side (13101 west, 13102 east) and Sapporo. Three station records: two lines at one
    station in 13101 (one group), one closed station in 13102. A 4 x 2 grid of 0.1 degree pixels with one missing."""
    db = duckdb.connect()
    db.execute('LOAD spatial')
    admin, stations, grid = tmp_path / 'admin.parquet', tmp_path / 'stations.parquet', tmp_path / 'pop.tif'
    db.execute(f"""COPY (SELECT code5, pref_code, name, population, ST_SetCRS(ST_GeomFromText(wkt), 'EPSG:4612') AS geometry FROM (VALUES
        ('13101', '13', '千代田区', 66680, 'POLYGON((139.0 35.8, 139.2 35.8, 139.2 36.0, 139.0 36.0, 139.0 35.8))'),
        ('13102', '13', '中央区', 169179, 'POLYGON((139.2 35.8, 139.4 35.8, 139.4 36.0, 139.2 36.0, 139.2 35.8))'),
        ('01100', '01', '札幌市', 1973395, 'POLYGON((141.2 43.0, 141.4 43.0, 141.4 43.1, 141.2 43.1, 141.2 43.0))'))
        AS t(code5, pref_code, name, population, wkt)) TO '{admin}' (FORMAT parquet)""")
    db.execute(f"""COPY (SELECT station_cd, station_g_cd, line_cd, station_name, e_status, lon, lat,
                               ST_SetCRS(ST_Point(lon, lat), 'OGC:CRS84') AS geometry FROM (VALUES
        (1, 1, 11, '東京', 0, 139.1, 35.9),
        (2, 1, 12, '東京', 0, 139.1, 35.9),
        (3, 3, 13, '築地', 2, 139.3, 35.9))
        AS t(station_cd, station_g_cd, line_cd, station_name, e_status, lon, lat)) TO '{stations}' (FORMAT parquet)""")
    values = numpy.array([[1, 2, 10, 20], [NODATA, 4, 30, 40]], dtype='float32')
    with rasterio.open(grid, 'w', driver='GTiff', width=4, height=2, count=1, dtype='float32', crs='EPSG:4326',
                       transform=from_origin(139.0, 36.0, 0.1, 0.1), nodata=NODATA) as dst:
        dst.write(values, 1)
    tables = {(ADMIN, 'municipalities'): str(admin), (STATIONS, 'station'): str(stations)}
    monkeypatch.setattr(sys.modules['geo_voyager.control_primitives.read_table'], 'dataset_url', lambda d, t: tables[(d, t)])
    monkeypatch.setattr(sys.modules['geo_voyager.control_primitives.population_grid'], 'dataset_url', {WORLDPOP: str(grid)}.__getitem__)
    yield db
    db.close()



def test_a_station_is_put_in_its_ward_by_a_spatial_join(connection):
    # The relational API drops the aliases after a join; SQL over the relations, named by their variables, keeps them.
    wards_ = wards(connection)
    stations = read_table(connection, STATIONS, 'station')
    rows = connection.sql("""SELECT w.name, count(*) AS records, count(DISTINCT s.station_g_cd) AS stations
                             FROM wards_ w JOIN stations s ON ST_Contains(w.geometry, s.geometry)
                             GROUP BY w.name ORDER BY w.name""").fetchall()
    assert rows == [('中央区', 1, 1), ('千代田区', 2, 1)]
    open_now = connection.sql("""SELECT count(DISTINCT s.station_g_cd) FROM wards_ w JOIN stations s
                                 ON ST_Contains(w.geometry, s.geometry) WHERE s.e_status = 0""").fetchone()[0]
    assert open_now == 1


def test_the_grid_is_summed_over_the_zones_it_is_given(connection):
    sums = sum_population_grid(connection, wards(connection))
    assert sums.columns == ['code5', 'pref_code', 'name', 'population', 'estimated_population']
    assert sums.order('code5').project('code5, estimated_population').fetchall() == [('13101', 7.0), ('13102', 100.0)]


def test_the_older_call_that_names_the_dataset_still_works(connection):
    assert sum_population_grid(WORLDPOP, connection, wards(connection)).count('*').fetchone()[0] == 2


@pytest.mark.parametrize('call', [
    lambda c: sum_population_grid(ADMIN, c, Mock()),
    lambda c: read_table(c, ADMIN, 'stations'),
])
def test_a_wrong_dataset_or_table_fails_before_reading(call):
    connection = Mock()
    with pytest.raises(ValueError):
        call(connection)
    connection.read_parquet.assert_not_called()


def test_zones_without_a_geometry_are_refused(connection):
    with pytest.raises(ValueError, match='geometry'):
        sum_population_grid(connection, read_table(connection, ADMIN, 'municipalities').project('code5, name'))


def test_too_many_zones_are_refused_before_the_grid_is_read(connection, monkeypatch):
    monkeypatch.setattr('geo_voyager.control_primitives.population_grid.MAX_ZONES', 1)
    monkeypatch.setattr('rasterio.open', Mock(side_effect=AssertionError('read')))
    with pytest.raises(ValueError, match='1'):
        sum_population_grid(connection, wards(connection))


def test_a_missing_value_read_as_none_by_a_foreign_gdal_is_still_skipped(connection, monkeypatch):
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
    sums = sum_population_grid(connection, wards(connection))
    assert sums.order('code5').project('estimated_population').fetchall()[0] == (7.0,)


def test_the_seed_skills_still_read_the_wider_tables(connection, monkeypatch):
    """The seed Skills were written when the tables had three columns; they must name the columns they unpack."""
    from pathlib import Path
    from geo_voyager.skill_library import SkillLibrary, link
    import geo_voyager.control_primitives as module

    def fresh():
        db = duckdb.connect()
        db.execute('LOAD spatial')
        return db

    monkeypatch.setattr(module, 'connect_duckdb', fresh)
    # The seeds read through read_table (ADR 0010): the fixture already points it at its files.
    library = SkillLibrary(Path(__file__).resolve().parents[1] / 'skill_library')

    def run(call):
        namespace = {}
        exec(link(f'result = {call}', library), namespace)
        return namespace['result']

    wards = "code5 BETWEEN '13101' AND '13123'"
    assert run(f"most_populous_area(where={wards!r})") == {'code5': '13102', 'name': '中央区', 'population': 169179}
    assert run(f"least_populous_area(where={wards!r})")['name'] == '千代田区'
    assert [a['name'] for a in run(f"top_areas_by_population(2, where={wards!r})")] == ['中央区', '千代田区']
    assert run(f"total_population(where={wards!r})") == 235859
    assert run("most_populous_area()")['name'] == '札幌市'
    assert run("count_station_records()") == 3
    assert run("northernmost_station()")['name'] in ('東京', '築地')
