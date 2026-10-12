"""sum_population_grid in the worker, reading the WorldPop COG by Range through the Gateway.

The reference sums were made on the host with rasterio from the whole downloaded COG and the same boundaries
(pixel centres, 2026-10-12). Taito's 214,562 is also the number Autonomous-GeoAI's WorldPop notes record.
"""
import json

from bench.infra import WORKER_IMAGE, benchmark_environment
from geo_voyager.docker_sandbox import DockerSandbox

CODE = '''
import json
from geo_voyager.control_primitives import connect_duckdb, sum_population_grid
with connect_duckdb() as connection:
    rows = sum_population_grid('yuiseki/worldpop-jp-2026-01', connection, area='東京都23区').order('code5').fetchall()
print(json.dumps(rows, ensure_ascii=False))
'''


def test_the_worker_sums_the_100m_grid_per_ward_through_the_gateway():
    with benchmark_environment() as names:
        rows = json.loads(DockerSandbox(image=WORKER_IMAGE, network=names['internal']).run(CODE))
    by_name = {name: population for _, name, population in rows}
    assert len(rows) == 23
    assert round(by_name['台東区']) == 214562
    assert round(by_name['世田谷区']) == 961312
    assert abs(sum(by_name.values()) - 9653022.28) < 1  # the census's 23 wards: 9,733,276
