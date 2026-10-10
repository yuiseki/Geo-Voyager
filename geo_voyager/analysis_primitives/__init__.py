"""Control Primitives of the analysis sandbox.

The data is fixed on the host and mounted read-only at /data; nothing is fetched at run time. Results that are
not a short JSON line (maps, tables) are written under /out, the one writable place that is kept after the run.
"""
from .data import connect_duckdb, data_path, output_path

__all__ = ['connect_duckdb', 'data_path', 'output_path']
