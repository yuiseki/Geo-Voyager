from pathlib import Path
import subprocess
import time

from integration.test_tokyo23_gateway import docker


def gateway_code():
    root = Path(__file__).resolve().parents[1] / 'geo_voyager'
    files = {name: (root / name).read_text() for name in (
        '__init__.py', 'dataset.py', 'dataset_graph.py', 'fetch_gateway.py',
        'service.py', 'service_graph.py', 'services.py', 'service_gateway.py',
    )}
    return f'''
from pathlib import Path
import sys
root = Path('/tmp/geo_voyager')
root.mkdir()
for name, content in {files!r}.items():
    (root / name).write_text(content)
sys.path.insert(0, '/tmp')
from geo_voyager.services import load_service_graph
from geo_voyager.service_gateway import make_handler
from http.server import HTTPServer
class LoggedHandler(make_handler(load_service_graph())):
    def send_response(self, code, message=None):
        print(self.command, self.path, code, flush=True)
        super().send_response(code, message)
HTTPServer(('0.0.0.0', 8000), LoggedHandler).serve_forever()
'''


def wait_for_gateway(name):
    for _ in range(60):
        result = subprocess.run(['docker', 'exec', name, 'python', '-c',
            "import socket; socket.create_connection(('127.0.0.1',8000),timeout=1).close()"],
            capture_output=True, timeout=5)
        if result.returncode == 0:
            return
        time.sleep(0.1)
    raise AssertionError(docker('logs', name))
