"""The environment every benchmark script runs in: isolated worker, one Gateway serving the
registered services and datasets, and the pinned GeoSPARQL server."""
from contextlib import contextmanager
import subprocess

from geo_voyager.dataset_mirror import ensure_mirror
from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_service_learning import pinned_geosparql

WORKER_IMAGE = 'geo-voyager-worker:duckdb-1.5.6-rasterio-1.5.1'
# The default 128m Gateway was OOM-killed mid-run while it relayed Parquet range reads.
GATEWAY_MEMORY = '1g'
DATASET_RESOLVE_ATTEMPTS = 400  # each 0.5 s: resolving the Parquet URLs needs the Internet


@contextmanager
def benchmark_environment():
    mirror = ensure_mirror()
    with network_topology(isolated=True, gateway_code=gateway_code(with_datasets=True, mirror_dir='/mirror'),
                          worker_image=WORKER_IMAGE, include_origin=False, gateway_memory=GATEWAY_MEMORY,
                          gateway_mounts=((str(mirror), '/mirror'),)) as names:
        wait_for_gateway(names['gateway'], start=True, attempts=DATASET_RESOLVE_ATTEMPTS)
        with pinned_geosparql(names):
            yield names


def environment_problem(names) -> str | None:
    """Why the environment can no longer answer, or None. The Gateway must run and reach the GeoSPARQL server.

    A cleanup once removed the containers of a running exploration; every later step failed on name resolution and
    the run recorded those failures as if the model had made them.
    """
    probe = ("from urllib.request import urlopen; "
             "print(urlopen('http://geosparql:3030/geo/sparql?query=ASK%7B%7D', timeout=5).status)")
    try:
        result = subprocess.run(['docker', 'exec', names['gateway'], 'python', '-c', probe],
                                capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return 'the Gateway did not answer within 30 s'
    if result.returncode != 0:
        return (result.stderr.strip().splitlines() or ['the GeoSPARQL probe failed'])[-1]
    return None
