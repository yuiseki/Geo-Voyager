"""The environment every benchmark script runs in: isolated worker, one Gateway serving the
registered services and datasets, and the pinned GeoSPARQL server."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import subprocess

from geo_voyager.dataset_mirror import ensure_mirror
from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_service_learning import pinned_geosparql

WORKER_IMAGE = 'geo-voyager-worker:duckdb-1.5.6-rasterio-1.5.1'
# The default 128m Gateway was OOM-killed mid-run while it relayed Parquet range reads.
GATEWAY_MEMORY = '1g'
DATASET_RESOLVE_ATTEMPTS = 400  # each 0.5 s: resolving the Parquet URLs needs the Internet


ROOT = Path(__file__).resolve().parents[1]
# Where docker/worker/Dockerfile copies the package; the whole of control_primitives is copied.
IMAGE_PACKAGE = '/usr/local/lib/python3.12/site-packages/geo_voyager'
WHOLE_IN_IMAGE = 'control_primitives/'


def _repository_files(root: Path) -> dict[str, Path]:
    package = root / 'geo_voyager'
    return {path.relative_to(package).as_posix(): path for path in package.rglob('*')
            if path.is_file() and '__pycache__' not in path.parts}


def image_drift(in_image: dict[str, str], root: Path = ROOT) -> list[str]:
    """The package files that differ between the worker image (path: sha256) and the repository: changed, or
    added to control_primitives, or gone from the repository since the image was built."""
    files = _repository_files(root)
    compared = set(in_image) | {path for path in files if path.startswith(WHOLE_IN_IMAGE)}
    return sorted(path for path in compared
                  if path not in files or path not in in_image
                  or hashlib.sha256(files[path].read_bytes()).hexdigest() != in_image[path])


def image_files(image: str) -> dict[str, str]:
    """The sha256 of each file of the package inside the image."""
    probe = ("import hashlib, json, pathlib; root = pathlib.Path(%r); "
             "print(json.dumps({p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() "
             "for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}))" % IMAGE_PACKAGE)
    result = subprocess.run(['docker', 'run', '--rm', '--pull', 'never', '--network', 'none', image, 'python', '-I', '-B',
                             '-c', probe], capture_output=True, text=True, check=True, timeout=60)
    return json.loads(result.stdout)


def require_current_image(image: str = WORKER_IMAGE) -> None:
    """Refuse an image built before the repository's code changed: the primitives run inside it, and a run on old
    primitives (DuckDB 64 MB when the repository said 512 MB) records their failures as the model's."""
    drift = image_drift(image_files(image))
    if drift:
        raise RuntimeError(f'the worker image {image} is older than the repository ({", ".join(drift)}); build it again: '
                           f'docker build --tag {image} --file docker/worker/Dockerfile .')


@contextmanager
def benchmark_environment():
    require_current_image()
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
