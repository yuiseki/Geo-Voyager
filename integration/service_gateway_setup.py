import json
from pathlib import Path
import subprocess
import time

from integration.test_tokyo23_gateway import docker


def _where_tables_are_read(references: str) -> str:
    """Of the dataset references, what geo_voyager.dataset_tables reads: each table's name and file, and the card's
    revision. The Gateway's code goes to `python -c` as one argument, which Linux caps at 128 KiB; the whole
    references (91 KB of mostly Japanese text, 2026-10-17) took it over."""
    data = json.loads(references)
    kept = {dataset_id: {'card_revision': reference['card_revision'],
                         'tables': [{'name': table['name'], 'read': table['read']} for table in reference['tables']]}
            for dataset_id, reference in data['datasets'].items()}
    return json.dumps({'source': {}, 'datasets': kept})


def gateway_code(*, with_datasets=False, mirror_dir=None):
    """Service Gateway. with_datasets also serves the registered Parquet datasets.

    mirror_dir is where the Gateway finds local copies of the tables (geo_voyager.dataset_mirror), inside its container.
    Dataset download URLs are resolved at startup, so the gateway waits for /tmp/start,
    which wait_for_gateway(start=True) touches once the external network is attached.
    """
    root = Path(__file__).resolve().parents[1] / 'geo_voyager'
    names = ['__init__.py', 'dataset.py', 'dataset_graph.py', 'fetch_gateway.py',
             'service.py', 'service_graph.py', 'services.py', 'service_gateway.py', 'execution_failure.py']
    if with_datasets:
        names += ['datasets.py', 'dataset_tables.py', 'dataset_references.json']
    files = {name: (root / name).read_text() for name in names}
    if 'dataset_references.json' in files:
        files['dataset_references.json'] = _where_tables_are_read(files['dataset_references.json'])
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
datasets, tables = None, None
if {with_datasets!r}:
    while not Path('/tmp/start').exists():
        time.sleep(0.05)
    from geo_voyager.datasets import load_dataset_graph
    # The gateway follows the Hub's resolve/ redirect on every request: a signed CDN URL
    # fixed at start expires after an hour, which a slow round outlives.
    datasets = load_dataset_graph()
    # Every table the dataset references list, at its pinned revision (ADR 0010).
    from geo_voyager.dataset_tables import TABLE_URLS as tables
class LoggedHandler(make_handler(load_service_graph(), datasets, tables, {mirror_dir!r})):
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
