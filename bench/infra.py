"""The environment every benchmark script runs in: isolated worker, one Gateway serving the
registered services and datasets, and the pinned GeoSPARQL server."""
from contextlib import contextmanager

from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_service_learning import pinned_geosparql

WORKER_IMAGE = 'geo-voyager-worker:duckdb-1.5.6'
# The default 128m Gateway was OOM-killed mid-run while it relayed Parquet range reads.
GATEWAY_MEMORY = '1g'
DATASET_RESOLVE_ATTEMPTS = 400  # each 0.5 s: resolving the Parquet URLs needs the Internet


@contextmanager
def benchmark_environment():
    with network_topology(isolated=True, gateway_code=gateway_code(with_datasets=True),
                          worker_image=WORKER_IMAGE, include_origin=False, gateway_memory=GATEWAY_MEMORY) as names:
        wait_for_gateway(names['gateway'], start=True, attempts=DATASET_RESOLVE_ATTEMPTS)
        with pinned_geosparql(names):
            yield names
