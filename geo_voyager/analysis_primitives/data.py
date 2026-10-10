import os
from pathlib import Path, PurePosixPath

# Set only by tests, which have no /data and /out.
DATA_ROOT = Path(os.environ.get('GEO_VOYAGER_ANALYSIS_DATA_ROOT', '/data'))
OUT_ROOT = Path(os.environ.get('GEO_VOYAGER_ANALYSIS_OUT_ROOT', '/out'))


def _inside(root: Path, name: str) -> Path:
    relative = PurePosixPath(name)
    if not name or relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'A name under the root is expected, not {name!r}')
    return root / relative


def data_path(name: str) -> str:
    """The path of a fixed data file, for example data_path('michiyomi/taito.parquet'). It must exist."""
    path = _inside(DATA_ROOT, name)
    if not path.is_file():
        available = sorted(str(p.relative_to(DATA_ROOT)) for p in DATA_ROOT.rglob('*') if p.is_file())
        raise FileNotFoundError(f'No data file {name!r}. Available: {available}')
    return str(path)


def output_path(name: str) -> str:
    """Where to write a result file (a map, a table), for example output_path('map.png'). Kept after the run."""
    path = _inside(OUT_ROOT, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def connect_duckdb(memory_limit: str = '4GB', threads: int = 4):
    """An in-memory DuckDB with the spatial extension, a memory cap, and spill to /tmp."""
    import duckdb
    connection = duckdb.connect(config={
        'extension_directory': '/opt/duckdb/extensions',
        'autoinstall_known_extensions': 'false',
        'autoload_known_extensions': 'false',
        'threads': str(threads),
        'memory_limit': memory_limit,
        'temp_directory': '/tmp/duckdb',
    })
    connection.execute('LOAD spatial')
    return connection
