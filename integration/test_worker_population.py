"""Worker.execute から実 Docker + 行政区 Parquet を読む明示的な確認。"""

import subprocess
import time

from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.worker import Worker
from integration.network_topology import network_topology
from integration.test_tokyo23_gateway import docker, gateway_code
from integration.test_worker_image import WORKER_IMAGE


def test_worker_execute_returns_most_populous_tokyo_ward():
    intent = Intent(
        text='東京都23区で人口が最も多い区と人口を求める',
        dataset_ids=('yuiseki/jp-admin-2026-09',),
    )
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
        observations = Worker(network=names['internal']).execute(intent)
        assert observations == [Observation(
            '東京都23区で人口が最も多い区は世田谷区で、人口は943664人である',
        )]
        logs = docker('logs', names['gateway'])
        assert 'GET 206 Range: bytes=' in logs
        print(repr(intent))
        print(observations[0].text)
        print(logs, end='')
    for role in ('worker', 'gateway'):
        assert names[role] not in docker('ps', '-a', '--format', '{{.Names}}')
    for role in ('internal', 'external'):
        assert names[role] not in docker('network', 'ls', '--format', '{{.Name}}')
