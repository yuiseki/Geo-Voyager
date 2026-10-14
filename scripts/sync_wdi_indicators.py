"""Write the indicator codes of the World Bank's WDI, with their names, to geo_voyager/wdi_indicators.tsv.

    .venv/bin/python scripts/sync_wdi_indicators.py

They are read from the series table at the revision the sandbox reads (geo_voyager.dataset_tables), one code a line
in the table's order, so that a code the model writes from memory can be checked without a model
(geo_voyager.indicator_codes).
"""
from pathlib import Path
import sys

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from geo_voyager.dataset_mirror import ensure_mirror, mirror_name  # noqa: E402
from geo_voyager.dataset_tables import TABLE_URLS  # noqa: E402
PATH = Path(__file__).resolve().parents[1] / 'geo_voyager' / 'wdi_indicators.tsv'  # geo_voyager.indicator_codes reads it

KEY = ('yuiseki/worldbank-wdi', 'series')


def main() -> None:
    url = TABLE_URLS[KEY]
    path = ensure_mirror(urls={KEY: url}) / mirror_name(url)
    rows = duckdb.connect().sql(
        'SELECT "Series Code", "Indicator Name" FROM read_parquet(?)', params=[str(path)]).fetchall()
    lines = ['code\tname'] + [f'{code}\t{" ".join(name.split())}' for code, name in rows]
    PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(len(rows), 'indicators from', url)


if __name__ == '__main__':
    main()
