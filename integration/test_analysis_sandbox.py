"""The analysis sandbox, for real: the libraries import, the data is readable and not writable, /out is kept,
there is no network, and the caps hold. Needs Docker, the geo-voyager-analysis image and the fixed data.
"""
import json
from dataclasses import replace
import subprocess

import pytest

from geo_voyager.analysis_data import FILES, data_root
from geo_voyager.docker_sandbox import ANALYSIS_PROFILE, DockerSandbox

IMAGE = 'geo-voyager-analysis:2026-10-10'


@pytest.fixture
def sandbox(tmp_path):
    if not all((data_root() / item.path).exists() for item in FILES):
        pytest.skip('The fixed analysis data is not in place (scripts/fix_analysis_data.py)')
    out = tmp_path / 'out'
    out.mkdir()
    out.chmod(0o777)        # the sandbox runs as 65534
    return DockerSandbox(image=IMAGE, profile=replace(ANALYSIS_PROFILE, data_dir=str(data_root()), out_dir=str(out))), out


def run_json(sandbox, code):
    return json.loads(sandbox.run(code).strip().splitlines()[-1])


def test_the_libraries_import_and_ortools_and_highspy_share_a_process(sandbox):
    box, _ = sandbox
    versions = run_json(box, '''
import json, ortools, highspy, sklearn, lightgbm, xgboost, catboost, statsmodels, scipy, numpy, shap, verde, networkx, matplotlib, rasterio, duckdb
from ortools.linear_solver import pywraplp
h = highspy.Highs(); h.setOptionValue("output_flag", False)
s = pywraplp.Solver.CreateSolver("SCIP"); x = s.IntVar(0, 3, "x"); s.Maximize(x); s.Solve()
print(json.dumps({"sklearn": sklearn.__version__, "duckdb": duckdb.__version__, "ortools_x": x.solution_value()}))
''')
    assert versions == {'sklearn': '1.9.1', 'duckdb': '1.5.6', 'ortools_x': 3.0}


def test_data_is_readable_but_not_writable_and_out_is_kept(sandbox):
    box, out = sandbox
    result = run_json(box, '''
import json, os
from geo_voyager.analysis_primitives import connect_duckdb, data_path, output_path
rows = connect_duckdb().sql(f"select count(*) from '{data_path('michiyomi/taito.parquet')}'").fetchone()[0]
try:
    open(data_path('michiyomi/taito.parquet'), 'ab'); writable = True
except OSError:
    writable = False
import matplotlib.pyplot as plt
plt.plot([0, 1]); plt.savefig(output_path('line.png'))
print(json.dumps({"rows": rows, "data_writable": writable}))
''')
    assert result == {'rows': 55_044, 'data_writable': False}
    assert (out / 'line.png').stat().st_size > 0


def test_there_is_no_network(sandbox):
    box, _ = sandbox
    result = run_json(box, '''
import json, socket
try:
    socket.create_connection(("huggingface.co", 443), timeout=5); reached = True
except OSError:
    reached = False
print(json.dumps({"reached": reached}))
''')
    assert result == {'reached': False}


def test_memory_beyond_the_cap_kills_the_run_not_the_host(sandbox):
    box, _ = sandbox
    with pytest.raises(subprocess.CalledProcessError) as raised:
        box.run('x = bytearray(9 * 1024 ** 3)\nx[::4096] = b"1" * len(x[::4096])\nprint("survived")')
    assert raised.value.returncode == 137          # killed by the cgroup's OOM killer
