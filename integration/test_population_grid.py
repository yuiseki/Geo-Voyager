"""sum_population_grid in the worker, reading the WorldPop COG by Range through the Gateway.

The reference sums were made on the host with rasterio from the whole downloaded COG and the same boundaries
(pixel centres, 2026-10-12). Taito's 214,562 is also the number GeoAI-master-skills' (formerly GeoAI-skills, and before that Autonomous-GeoAI) WorldPop notes record.
"""
import json

from bench.infra import WORKER_IMAGE, benchmark_environment
from geo_voyager.docker_sandbox import DockerSandbox

CODE = '''
import json
from geo_voyager.control_primitives import connect_duckdb, read_table, sum_population_grid
with connect_duckdb() as connection:
    wards = read_table(connection, 'yuiseki/jp-admin-2026-09', 'municipalities').filter(\"pref_code = '13' AND name LIKE '%区'\")
    rows = sum_population_grid(connection, wards).order('code5').project('code5, name, estimated_population').fetchall()
print(json.dumps(rows, ensure_ascii=False))
'''

# The station records in the 23 wards, in service, joined in space with the boundaries; made on the host from the
# whole files with the same join (2026-10-12).
STATIONS = '''
import json
from geo_voyager.control_primitives import connect_duckdb, read_table
with connect_duckdb() as connection:
    wards = read_table(connection, 'yuiseki/jp-admin-2026-09', 'municipalities').filter(\"pref_code = '13' AND name LIKE '%区'\")
    stations = read_table(connection, 'yuiseki/ekidata-jp', 'station')
    rows = connection.sql("""SELECT w.name, count(*), count(DISTINCT s.station_g_cd) FROM wards w JOIN stations s
                             ON ST_Contains(w.geometry, s.geometry) WHERE s.e_status = 0 GROUP BY w.name""").fetchall()
print(json.dumps(rows, ensure_ascii=False))
'''


def test_the_worker_sums_the_grid_per_ward_and_puts_stations_in_wards_through_the_gateway():
    with benchmark_environment() as names:
        sandbox = DockerSandbox(image=WORKER_IMAGE, network=names['internal'])
        rows = json.loads(sandbox.run(CODE))
        stations = json.loads(sandbox.run(STATIONS))
    by_ward = {name: (records, groups) for name, records, groups in stations}
    assert by_ward['世田谷区'] == (44, 38)
    assert sum(groups for _, groups in by_ward.values()) >= 458   # a station with platforms in two wards counts in each
    by_name = {name: population for _, name, population in rows}
    assert len(rows) == 23
    assert round(by_name['台東区']) == 214562
    assert round(by_name['世田谷区']) == 961312
    assert abs(sum(by_name.values()) - 9653022.28) < 1  # the census's 23 wards: 9,733,276


# All the municipalities, and a circle of 1 km around each operating station, each in one call within the sandbox's
# limits (2 GB, 180 s). Read by Range through the Gateway, 1,000 circles took 166 s; with the grid fetched to /tmp
# once and each part of a zone cut on its own, the municipalities took 45 s and 1,101 MB, the circles 25 s and
# 312 MB (2026-10-15). The municipalities hold 126,547,111 of the grid's 126,574,853.
ALL_JAPAN = '''
import json
from geo_voyager.control_primitives import connect_duckdb, read_table, sum_population_grid
with connect_duckdb() as connection:
    stations = read_table(connection, "yuiseki/ekidata-jp", "station").filter("e_status = 0")
    zones = ZONES
    print(json.dumps(sum_population_grid(connection, zones).aggregate("count(*), sum(estimated_population)").fetchone()))
'''
MUNICIPALITIES = 'read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities").filter("ward IS NULL AND geometry IS NOT NULL").project("code5, geometry")'
CIRCLES = '''connection.sql("""
        WITH p AS (SELECT station_g_cd, any_value(geometry) AS geometry FROM stations GROUP BY station_g_cd),
        z AS (SELECT *, 'EPSG:' || (32601 + CAST(floor((ST_X(geometry) + 180) / 6) AS INTEGER)) AS utm FROM p)
        SELECT station_g_cd, ST_Transform(ST_Buffer(ST_Transform(geometry, 'OGC:CRS84', utm), 1000), utm, 'OGC:CRS84') AS geometry FROM z""")'''


def test_the_grid_over_all_municipalities_and_every_stations_circle_fits_the_sandbox():
    with benchmark_environment() as names:
        sandbox = DockerSandbox(image=WORKER_IMAGE, network=names['internal'])
        municipalities = json.loads(sandbox.run(ALL_JAPAN.replace('ZONES', MUNICIPALITIES)))
        circles = json.loads(sandbox.run(ALL_JAPAN.replace('ZONES', CIRCLES)))
    assert municipalities[0] == 1741 and round(municipalities[1]) == 126547111
    assert circles[0] == 8766 and round(circles[1]) == 118634044       # the circles overlap: people counted again
