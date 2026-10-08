"""検証済みの sandbox 接続と Gateway 経由の行政区域読み込み。"""

from .connect_duckdb import connect_duckdb
from .dataset_url import dataset_url
from .load_admin_units import load_admin_units

__all__ = ["connect_duckdb", "dataset_url", "load_admin_units"]
