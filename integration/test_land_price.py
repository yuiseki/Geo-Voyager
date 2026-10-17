"""The land prices of 2026 in the worker, through the Gateway, joined to the municipalities by their code.

The expected numbers are those GeoAI-master-skills measured for its reference (ksj-l01-land-price, 2026-10-16):
25,565 lots in 2026, the highest at 中央区銀座 4 丁目, 67,100,000 yen per m².
"""
import json

from bench.infra import WORKER_IMAGE, benchmark_environment
from geo_voyager.docker_sandbox import DockerSandbox

CODE = '''
import json
from geo_voyager.control_primitives import connect_duckdb, read_table
with connect_duckdb() as connection:
    prices = read_table(connection, "yuiseki/ksj-l01-land-price", "land_price")
    municipalities = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities")
    count, = prices.aggregate("count(*)").fetchone()
    top = prices.order("price_yen DESC").project("price_yen, address").fetchone()
    joined = connection.sql("""SELECT m.name, count(*) FROM prices p JOIN municipalities m ON p.municipality_code = m.code5
                               WHERE m.pref_code = '13' GROUP BY m.name ORDER BY 2 DESC LIMIT 1""").fetchone()
print(json.dumps([count, top, joined], ensure_ascii=False))
'''


def test_the_worker_reads_the_land_prices_and_joins_them_to_the_municipalities():
    with benchmark_environment() as names:
        count, (price, address), (name, lots) = json.loads(
            DockerSandbox(image=WORKER_IMAGE, network=names['internal']).run(CODE))
    assert count == 25565
    assert price == 67100000 and '銀座' in address
    assert lots > 0 and name
