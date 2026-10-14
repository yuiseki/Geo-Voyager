"""build と network none での extension LOAD。実データ処理より先に明示実行する。"""

from pathlib import Path
import subprocess

from geo_voyager.docker_sandbox import DockerSandbox

WORKER_IMAGE = "geo-voyager-worker:duckdb-1.5.6-rasterio-1.5.1"


def test_worker_image_build_and_offline_extensions():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["docker", "build", "--tag", WORKER_IMAGE, "--file", "docker/worker/Dockerfile", "."],
        cwd=root, capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    code = '''
import os, runpy
assert os.getuid() == 65534
assert not os.access('/opt/duckdb/extensions', os.W_OK)
scope = runpy.run_path('/opt/geo_voyager/analyze_tokyo23.py')
with scope['connect']() as con:
    assert con.execute("SELECT current_setting('autoinstall_known_extensions')").fetchone()[0] is False
    assert con.execute("SELECT current_setting('autoload_known_extensions')").fetchone()[0] is False
    assert con.execute("SELECT current_setting('allow_unsigned_extensions')").fetchone()[0] is False
    assert con.execute("SELECT count(*) FROM duckdb_extensions() WHERE extension_name IN ('httpfs', 'spatial') AND loaded").fetchone()[0] == 2
    print('duckdb extensions ok')
import rasterio
assert rasterio.__version__ == '1.5.1' and 'GTiff' in rasterio.drivers.raster_driver_extensions().values()
'''
    stdout = DockerSandbox(image=WORKER_IMAGE).run(code)
    assert stdout == "duckdb extensions ok\n"
    print(stdout, end="")


def test_duckdb_spills_to_the_sandboxs_tmpfs_when_a_query_outgrows_its_memory():
    # The small tasks of GeoAI-skills (2026-10-14), task 15: a self join of the 1,918 municipalities' faces outgrew
    # the memory limit, and DuckDB failed to create its temporary directory ".tmp" in the read-only working directory.
    code = '''
from geo_voyager.control_primitives import connect_duckdb
with connect_duckdb() as con:
    assert con.execute("SELECT current_setting('temp_directory')").fetchone()[0].startswith('/tmp/')
    con.execute("SET memory_limit='64MB'")
    con.execute("SET preserve_insertion_order=false")
    rows = con.execute("SELECT count(*) FROM (SELECT md5(i::VARCHAR) AS k FROM range(3000000) t(i) ORDER BY k)").fetchone()[0]
    print(rows)
'''
    assert DockerSandbox(image=WORKER_IMAGE).run(code) == "3000000\n"
