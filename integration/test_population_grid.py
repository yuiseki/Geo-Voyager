"""sum_population_grid in the worker, reading the WorldPop COG by Range through the Gateway.

The reference sums were made on the host with rasterio from the whole downloaded COG and the same boundaries
(pixel centres, 2026-10-12). Taito's 214,562 is also the number GeoAI-skills' (formerly Autonomous-GeoAI) WorldPop notes record.
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
