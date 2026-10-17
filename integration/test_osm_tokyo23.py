"""OpenStreetMap of the 23 wards in the worker, through the Gateway: read, turned to longitude and latitude, joined.

The ward boundaries are those GeoAI-master-skills counted for its reference (osm-tokyo23-src-2026-08, 2026-10-14):
24 areas of boundary = administrative, admin_level = 7 named ...区, under 23 names. The polygons are the largest of
the four tables (1,437,105 rows, 151 MB); the sandbox has 2 GB and 180 s.
"""
import json
import time

from bench.infra import WORKER_IMAGE, benchmark_environment
from geo_voyager.docker_sandbox import DockerSandbox

CODE = '''
import json
from geo_voyager.control_primitives import connect_duckdb, read_table
with connect_duckdb() as connection:
    polygons = read_table(connection, "yuiseki/osm-tokyo23-src-2026-08", "planet_osm_polygon")
    boundaries = polygons.filter("boundary = 'administrative' AND admin_level = '7' AND name LIKE '%区'")
    rows, names = boundaries.aggregate("count(*), count(DISTINCT name)").fetchone()
    lon, lat = boundaries.filter("name = '台東区'").project("ST_X(ST_Centroid(way)), ST_Y(ST_Centroid(way))").fetchone()
    wards = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities").filter("pref_code = '13' AND name LIKE '%区'")
    courts = polygons.filter("leisure = 'pitch' AND sport = 'tennis'")
    in_wards = connection.sql("""SELECT count(*) FROM courts c JOIN wards w ON ST_Within(ST_Centroid(c.way), w.geometry)""").fetchone()[0]
print(json.dumps([rows, names, lon, lat, in_wards]))
'''


def test_the_worker_reads_osm_of_the_23_wards_in_longitude_and_latitude_and_joins_it_to_the_wards():
    with benchmark_environment() as names:
        started = time.time()
        rows, distinct, lon, lat, courts = json.loads(DockerSandbox(image=WORKER_IMAGE, network=names['internal']).run(CODE))
        elapsed = time.time() - started
    assert (rows, distinct) == (24, 23)
    assert 139.7 < lon < 139.83 and 35.69 < lat < 35.74                         # 台東区, in degrees, not metres
    assert courts > 100
    print(f'tennis courts in the wards: {courts}, {elapsed:.0f} s')
