"""実 Internet を使う固定実験。offline extension test 成功後に明示実行する。"""

import json
from pathlib import Path
import subprocess
import time

from integration.network_topology import network_topology
from integration.test_worker_image import WORKER_IMAGE


def gateway_code():
    root = Path(__file__).resolve().parents[1]
    files = {name: (root / 'geo_voyager' / name).read_text() for name in (
        '__init__.py', 'dataset.py', 'dataset_graph.py', 'datasets.py', 'fetch_gateway.py',
    )}
    resolver = (root / 'integration/admin_download.py').read_text()
    return f'''
from pathlib import Path
import sys, time
root = Path('/tmp/geo_voyager')
root.mkdir()
for name, contents in {files!r}.items():
    (root / name).write_text(contents)
sys.path.insert(0, '/tmp')
# external network 接続後に実験を開始するためのテスト用合図。
while not Path('/tmp/start').exists():
    time.sleep(0.05)
from geo_voyager.datasets import load_dataset_graph
from geo_voyager.fetch_gateway import make_handler
from http.server import HTTPServer
exec({resolver!r})
graph = load_dataset_graph()
register_admin_download(graph)
print('registered administrative parquet download', flush=True)
class LoggedHandler(make_handler(graph)):
    def send_response(self, code, message=None):
        print(self.command, code, 'Range:', self.headers.get('Range', ''), flush=True)
        super().send_response(code, message)
HTTPServer(('0.0.0.0', 8000), LoggedHandler).serve_forever()
'''


def docker(*args, timeout=30):
    return subprocess.check_output(['docker', *args], text=True, timeout=timeout)


def test_tokyo23_parquet_through_gateway():
    with network_topology(isolated=True, gateway_code=gateway_code(),
                          worker_image=WORKER_IMAGE, include_origin=False) as names:
        docker('exec', names['gateway'], 'python', '-c', "from pathlib import Path; Path('/tmp/start').touch()")
        for attempt in range(60):
            ready = subprocess.run(
                ['docker', 'exec', names['gateway'], 'python', '-c',
                 "import socket; socket.create_connection(('127.0.0.1',8000),timeout=1).close()"],
                capture_output=True, timeout=5,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        assert ready.returncode == 0, docker('logs', names['gateway'])
        worker = json.loads(docker('inspect', names['worker']))[0]
        gateway = json.loads(docker('inspect', names['gateway']))[0]
        assert set(worker['NetworkSettings']['Networks']) == {names['internal']}
        assert set(gateway['NetworkSettings']['Networks']) == {names['internal'], names['external']}
        assert worker['Mounts'] == [] and gateway['Mounts'] == []
        assert worker['HostConfig']['PidsLimit'] == 128
        assert worker['HostConfig']['ReadonlyRootfs'] is True
        output = docker('exec', names['worker'], 'python', '-I', '-B',
                        '/opt/geo_voyager/analyze_tokyo23.py', timeout=60)
        assert 'rows=23\n' in output
        total = int(output.split('population_total=')[1].strip())
        assert total > 0
        area_counts = docker('exec', names['worker'], 'python', '-I', '-B', '-c',
            "from geo_voyager.control_primitives import connect_duckdb, load_admin_units; "
            "c=connect_duckdb(); "
            "all_count=load_admin_units('yuiseki/jp-admin-2026-09',c,area=None).count('*').fetchone()[0]; "
            "tokyo_count=load_admin_units('yuiseki/jp-admin-2026-09',c,area='東京都23区').count('*').fetchone()[0]; "
            "assert all_count>23 and tokyo_count==23; print('all / Tokyo23:',all_count,tokyo_count)",
            timeout=60)
        print(area_counts, end='')
        logs = docker('logs', names['gateway'])
        assert 'GET 206 Range: bytes=' in logs, logs
        print(output, end='')
        print(logs, end='')
        ip = docker('exec', names['gateway'], 'python', '-c',
                    "import socket; print(socket.gethostbyname('huggingface.co'))").strip()
        blocked = f'''
import socket
try:
    socket.create_connection(({ip!r}, 443), timeout=2)
except OSError:
    print('Worker direct Internet: blocked')
else:
    raise AssertionError('Worker reached Internet directly')
'''
        print(docker('exec', names['worker'], 'python', '-c', blocked), end='')
    for role in ('worker', 'gateway'):
        assert names[role] not in docker('ps', '-a', '--format', '{{.Names}}')
    for role in ('internal', 'external'):
        assert names[role] not in docker('network', 'ls', '--format', '{{.Name}}')
