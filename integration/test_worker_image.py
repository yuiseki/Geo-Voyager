"""build と network none での extension LOAD。実データ処理より先に明示実行する。"""

from pathlib import Path
import subprocess

from geo_voyager.docker_sandbox import DockerSandbox

WORKER_IMAGE = "geo-voyager-worker:duckdb-1.5.6"


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
'''
    stdout = DockerSandbox(image=WORKER_IMAGE).run(code)
    assert stdout == "duckdb extensions ok\n"
    print(stdout, end="")
