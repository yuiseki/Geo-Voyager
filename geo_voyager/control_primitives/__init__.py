"""生成コードが使う部品。DuckDB の接続、Gateway 経由の表の読み込み（read_table）、人口格子の区域ごとの合計、サービスの呼び出し。"""

from .call_service import call_service
from .connect_duckdb import connect_duckdb
from .dataset_url import dataset_url
from .population_grid import sum_population_grid
from .read_table import read_table

__all__ = ["call_service", "connect_duckdb", "dataset_url", "read_table", "sum_population_grid"]
