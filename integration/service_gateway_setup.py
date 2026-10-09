from pathlib import Path
import subprocess
import time

from integration.test_tokyo23_gateway import docker


def gateway_code(*, with_datasets=False):
    """Service Gateway. with_datasets also serves the registered Parquet datasets.

    Dataset download URLs are resolved at startup, so the gateway waits for /tmp/start,
    which wait_for_gateway(start=True) touches once the external network is attached.
    """
    root = Path(__file__).resolve().parents[1] / 'geo_voyager'
    names = ['__init__.py', 'dataset.py', 'dataset_graph.py', 'fetch_gateway.py',
             'service.py', 'service_graph.py', 'services.py', 'service_gateway.py', 'execution_failure.py']
    if with_datasets:
        names.append('datasets.py')
    files = {name: (root / name).read_text() for name in names}
    resolver = (Path(__file__).resolve().parent / 'admin_download.py').read_text() if with_datasets else ''
    return f'''
from pathlib import Path
import sys
root = Path('/tmp/geo_voyager')
root.mkdir()
for name, content in {files!r}.items():
    (root / name).write_text(content)
sys.path.insert(0, '/tmp')
import time
from geo_voyager.services import load_service_graph
from geo_voyager.service_gateway import make_handler
from http.server import HTTPServer
datasets = None
if {with_datasets!r}:
    while not Path('/tmp/start').exists():
        time.sleep(0.05)
    from geo_voyager.datasets import load_dataset_graph
    exec({resolver!r})
    datasets = load_dataset_graph()
    for attempt in range(5):  # the route to the external network can lag behind the attach
        try:
            register_admin_download(datasets)
            register_station_download(datasets)
            break
        except OSError:
            if attempt == 4:
                raise
            time.sleep(2)
class LoggedHandler(make_handler(load_service_graph(), datasets)):
    def send_response(self, code, message=None):
        print(self.command, self.path, code, flush=True)
        super().send_response(code, message)
HTTPServer(('0.0.0.0', 8000), LoggedHandler).serve_forever()
'''


def wait_for_gateway(name, *, start=False, attempts=60):
    if start:
        subprocess.run(['docker', 'exec', name, 'python', '-c',
                        "from pathlib import Path; Path('/tmp/start').touch()"], check=True, capture_output=True, timeout=10)
    for _ in range(attempts):
        result = subprocess.run(['docker', 'exec', name, 'python', '-c',
            "import socket; socket.create_connection(('127.0.0.1',8000),timeout=1).close()"],
            capture_output=True, timeout=5)
        if result.returncode == 0:
            return
        time.sleep(0.1 if not start else 0.5)
    raise AssertionError(docker('logs', name))
