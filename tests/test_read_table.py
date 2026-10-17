"""read_table reads any Parquet table a dataset reference lists, under the reference's column names (ADR 0010)."""
import sys

import duckdb
import pytest

from geo_voyager.control_primitives import read_table
from geo_voyager.control_primitives.dataset_url import dataset_url

ADMIN, STATIONS = 'yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp'
OSM = 'yuiseki/osm-tokyo23-src-2026-08'


@pytest.fixture
def connection(tmp_path, monkeypatch):
    """Two wards labelled JGD2000 as in jp-admin, and two station records in OGC:CRS84 as in ekidata."""
    db = duckdb.connect()
    db.execute('LOAD spatial')
    admin, stations, lines = tmp_path / 'admin.parquet', tmp_path / 'stations.parquet', tmp_path / 'lines.parquet'
    db.execute(f"""COPY (SELECT code5, pref_code, name, ward, population, ST_SetCRS(ST_GeomFromText(wkt), 'EPSG:4612') AS geometry
        FROM (VALUES ('13101', '13', '千代田区', NULL, 66680, 'POLYGON((139.0 35.8, 139.2 35.8, 139.2 36.0, 139.0 36.0, 139.0 35.8))'),
                     ('13102', '13', '中央区', NULL, 169179, 'POLYGON((139.2 35.8, 139.4 35.8, 139.4 36.0, 139.2 36.0, 139.2 35.8))'))
        AS t(code5, pref_code, name, ward, population, wkt)) TO '{admin}' (FORMAT parquet)""")
    db.execute(f"""COPY (SELECT station_cd, station_g_cd, line_cd, station_name, e_status, lon, lat,
                               ST_SetCRS(ST_Point(lon, lat), 'OGC:CRS84') AS geometry
        FROM (VALUES (1, 1, 11, '東京', 0, 139.1, 35.9), (3, 3, 13, '築地', 2, 139.3, 35.9))
        AS t(station_cd, station_g_cd, line_cd, station_name, e_status, lon, lat)) TO '{stations}' (FORMAT parquet)""")
    db.execute(f"COPY (SELECT 11 AS line_cd, '山手線' AS line_name) TO '{lines}' (FORMAT parquet)")
    # A node of OSM as osm2pgsql writes it, in Web Mercator metres: (139.1, 35.9) in the first ward.
    osm = tmp_path / 'osm.parquet'
    db.execute(f"""COPY (SELECT 1 AS osm_id, 'cafe' AS amenity,
                        ST_SetCRS(ST_Transform(ST_Point(139.1, 35.9), 'OGC:CRS84', 'EPSG:3857', always_xy := true), 'EPSG:3857') AS way)
                  TO '{osm}' (FORMAT parquet)""")
    paths = {(ADMIN, 'municipalities'): str(admin), (STATIONS, 'station'): str(stations), (STATIONS, 'line'): str(lines),
             (OSM, 'planet_osm_point'): str(osm)}
    monkeypatch.setattr(sys.modules['geo_voyager.control_primitives.read_table'], 'dataset_url', lambda d, t: paths[(d, t)])
    yield db
    db.close()


def test_every_column_is_read_under_the_references_name(connection):
    stations = read_table(connection, STATIONS, 'station')
    assert stations.columns == ['station_cd', 'station_g_cd', 'line_cd', 'station_name', 'e_status', 'lon', 'lat', 'geometry']


def test_a_table_the_old_primitives_could_not_read_is_read(connection):
    assert read_table(connection, STATIONS, 'line').fetchall() == [(11, '山手線')]


def test_longitude_latitude_geometries_are_labelled_alike_so_they_join_in_space(connection):
    wards, stations = read_table(connection, ADMIN, 'municipalities'), read_table(connection, STATIONS, 'station')
    assert 'OGC:CRS84' in str(dict(zip(wards.columns, wards.types))['geometry'])
    joined = connection.sql('SELECT w.name, s.station_name FROM wards w JOIN stations s ON ST_Within(s.geometry, w.geometry) ORDER BY 1')
    assert joined.fetchall() == [('中央区', '築地'), ('千代田区', '東京')]


def test_an_area_is_a_condition_on_the_columns(connection):
    wards = read_table(connection, ADMIN, 'municipalities').filter("pref_code = '13' AND name LIKE '%区'")
    assert wards.aggregate('count(*), sum(population)').fetchone() == (2, 235859)


def test_a_table_that_is_not_listed_is_refused_with_the_ones_that_are(connection):
    with pytest.raises(ValueError, match='station, line, company, join, pref'):
        read_table(connection, STATIONS, 'stations')


def test_a_raster_is_not_read_as_a_table(connection):
    with pytest.raises(ValueError, match='sum_population_grid'):
        read_table(connection, 'yuiseki/worldpop-jp-2026-01', 'population_100m_2020')


def test_the_url_is_the_gateways_path_of_the_table():
    assert dataset_url(STATIONS, 'line') == 'http://gateway:8000/datasets/yuiseki/ekidata-jp/line'
    with pytest.raises(ValueError):
        dataset_url(STATIONS, 'nothing')


def test_a_web_mercator_geometry_is_turned_to_longitude_latitude_so_it_joins_the_others(connection):
    # osm2pgsql writes EPSG:3857 metres; the areas and distances the contract teaches are from OGC:CRS84.
    points, wards = read_table(connection, OSM, 'planet_osm_point'), read_table(connection, ADMIN, 'municipalities')
    assert 'OGC:CRS84' in str(dict(zip(points.columns, points.types))['way'])
    lon, lat = connection.sql('SELECT ST_X(way), ST_Y(way) FROM points').fetchone()
    assert abs(lon - 139.1) < 1e-9 and abs(lat - 35.9) < 1e-9
    joined = connection.sql('SELECT w.name FROM wards w JOIN points p ON ST_Within(p.way, w.geometry)').fetchall()
    assert joined == [('千代田区',)]
