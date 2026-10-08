"""固定テスト Dataset 1件を3コンテナ内で検証。実 Internet は使わない。"""

import json
from pathlib import Path
import subprocess
import time

from integration.network_topology import network_topology


ORIGIN_CODE = '''
from http.server import BaseHTTPRequestHandler, HTTPServer

class Origin(BaseHTTPRequestHandler):
    def reply(self, head=False):
        if self.path != "/fixed.txt":
            self.send_error(404)
            return
        body = b"0123456789"
        partial = not head and self.headers.get("Range") == "bytes=0-4"
        self.send_response(206 if partial else 200)
        if partial:
            self.send_header("Content-Range", "bytes 0-4/10")
            body = body[:5]
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        if not head:
            self.wfile.write(body)
    def do_GET(self): self.reply()
    def do_HEAD(self): self.reply(head=True)

HTTPServer(("0.0.0.0", 8000), Origin).serve_forever()
'''


def gateway_code():
    root = Path(__file__).resolve().parents[1] / "geo_voyager"
    files = {name: (root / name).read_text() for name in (
        "__init__.py", "dataset.py", "dataset_graph.py", "fetch_gateway.py",
    )}
    return f'''
from pathlib import Path
import sys
root = Path("/tmp/geo_voyager")
root.mkdir()
for name, contents in {files!r}.items():
    (root / name).write_text(contents)
sys.path.insert(0, "/tmp")
from http.server import HTTPServer
from geo_voyager.dataset import Dataset
from geo_voyager.dataset_graph import DatasetGraph
from geo_voyager.fetch_gateway import make_handler
graph = DatasetGraph()
graph.register(Dataset(
    id="test/fixed", description="固定テストデータ", url="http://origin:8000/fixed.txt",
    license="CC0", formats=("text",), spatial_coverage="なし",
    temporal_coverage="なし", contents=("テスト文字列",),
))
HTTPServer(("0.0.0.0", 8000), make_handler(graph)).serve_forever()
'''


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=30)


def test_fetch_gateway_over_isolated_docker_topology():
    with network_topology(isolated=True, gateway_code=gateway_code(), origin_code=ORIGIN_CODE) as names:
        # 固定 test server の起動待ちだけ。Gateway 自体に retry はない。
        for role in ("gateway", "origin"):
            code = "import socket; socket.create_connection(('127.0.0.1', 8000), timeout=1).close()"
            for attempt in range(30):
                result = subprocess.run(
                    ["docker", "exec", names[role], "python", "-c", code],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    break
                time.sleep(0.1)
            assert result.returncode == 0, docker("logs", names[role])

        def inspect(role):
            return json.loads(docker("inspect", names[role]))[0]
        assert set(inspect("worker")["NetworkSettings"]["Networks"]) == {names["internal"]}
        assert set(inspect("gateway")["NetworkSettings"]["Networks"]) == {names["internal"], names["external"]}
        origin = inspect("origin")
        assert set(origin["NetworkSettings"]["Networks"]) == {names["external"]}
        for role in ("worker", "gateway", "origin"):
            assert inspect(role)["Mounts"] == []

        checks = '''
from http.client import HTTPConnection

def request(method="GET", path="/datasets/test/fixed", headers=None):
    conn = HTTPConnection("gateway", 8000, timeout=5)
    try:
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()

assert request()[::2] == (200, b"0123456789")
print("GET: 200, 0123456789")
status, headers, body = request("HEAD")
assert status == 200 and body == b"" and headers["Content-Length"] == "10"
print("HEAD: 200, body empty, Content-Length 10")
status, headers, body = request(headers={"Range": "bytes=0-4"})
assert status == 206 and body == b"01234" and headers["Content-Range"] == "bytes 0-4/10"
print("Range GET: 206, 01234, bytes 0-4/10")
assert request(path="/datasets/unknown/dataset")[0] == 404
print("unknown dataset: 404")
for method in ("POST", "PUT", "PATCH", "DELETE"):
    assert request(method)[0] == 405
    print(method + ": 405")
assert request(path="/datasets/test/fixed?url=http://origin:8000/fixed.txt")[0] == 400
print("arbitrary URL query: 400")
'''
        print(docker("exec", names["worker"], "python", "-c", checks), end="")
        ip = origin["NetworkSettings"]["Networks"][names["external"]]["IPAddress"]
        direct = f'''
from http.client import HTTPConnection
for host in ("origin", {ip!r}):
    conn = HTTPConnection(host, 8000, timeout=2)
    try:
        conn.request("GET", "/fixed.txt")
        conn.getresponse()
    except OSError:
        print(host + ": direct access blocked")
    else:
        raise AssertionError("Worker reached Origin directly")
    finally:
        conn.close()
'''
        print(docker("exec", names["worker"], "python", "-c", direct), end="")

    for role in ("worker", "gateway", "origin"):
        assert names[role] not in docker("ps", "-a", "--format", "{{.Names}}")
    for role in ("internal", "external"):
        assert names[role] not in docker("network", "ls", "--format", "{{.Name}}")
