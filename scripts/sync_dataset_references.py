"""Copy the YAML frontmatter of the dataset references in GeoAI-skills (the How-to Graph) into
geo_voyager/dataset_references.json, at a fixed commit.

    uvx --with pyyaml --with 'duckdb==1.5.6' python scripts/sync_dataset_references.py ../GeoAI-skills <commit>

The references are measured facts about each dataset (what a row is, its ids and join keys, the keys it does not
have, what the main columns mean). GeoAI-skills is where they are kept; this copies the ones of the datasets the
sandbox can read, so that a run does not depend on another checkout and the commit it was made from is recorded.

A reference lists the main columns; the code needs every column's name and type. Those are measured here, from the
Parquet footer of each table at the revision the sandbox reads (geo_voyager.dataset_tables), and kept as the
table's "schema" with the date: not a fact of the reference, so it is marked as Geo-Voyager's measurement. So are
the row groups and the columns the file is split by (geo_voyager.contracts.parquet_layout).
"""
import datetime
import json
from pathlib import Path
import subprocess
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REFERENCES = {
    'yuiseki/jp-admin-2026-09': 'jp-admin-2026-09.md',
    'yuiseki/ekidata-jp': 'ekidata-jp.md',
    'yuiseki/worldpop-jp-2026-01': 'worldpop/japan.md',
}
DIRECTORY = '.agents/skills/dataset-discovery/references/'
OUT = Path(__file__).resolve().parents[1] / 'geo_voyager' / 'dataset_references.json'


def frontmatter(text: str) -> dict:
    if not text.startswith('---\n'):
        raise ValueError('the reference has no YAML frontmatter')
    return yaml.safe_load(text.split('---\n', 2)[1])


def main() -> None:
    repository, commit = sys.argv[1], sys.argv[2]
    commit = subprocess.run(['git', '-C', repository, 'rev-parse', commit], check=True, capture_output=True, text=True).stdout.strip()
    datasets = {}
    for dataset_id, path in REFERENCES.items():
        text = subprocess.run(['git', '-C', repository, 'show', f'{commit}:{DIRECTORY}{path}'],
                              check=True, capture_output=True, text=True).stdout
        datasets[dataset_id] = frontmatter(text)
        if datasets[dataset_id]['id'] != dataset_id:
            raise ValueError(f'{path} is about {datasets[dataset_id]["id"]}, not {dataset_id}')
    OUT.write_text(json.dumps({'source': {}, 'datasets': datasets}, ensure_ascii=False, default=str))
    from geo_voyager import dataset_tables
    from geo_voyager.contracts.parquet_layout import split_columns
    import importlib
    import duckdb
    importlib.reload(dataset_tables)
    connection = duckdb.connect()
    connection.execute('INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial')
    measured = datetime.date.today().isoformat()
    for (dataset_id, table_name), url in dataset_tables.TABLE_URLS.items():
        if url.endswith('.parquet'):
            table = next(t for t in datasets[dataset_id]['tables'] if t['name'] == table_name)
            columns = connection.execute(f"DESCRIBE SELECT * FROM read_parquet('{url}')").fetchall()
            row_groups, split_by = split_columns(connection, url)
            table['schema'] = {'measured_by': 'Geo-Voyager', 'measured_on': measured,
                               'columns': [[name, kind] for name, kind, *_ in columns],
                               'row_groups': row_groups, 'split_by': split_by}
    source = {'repository': 'https://github.com/yuiseki/GeoAI-skills', 'commit': commit,
              'paths': {dataset_id: DIRECTORY + path for dataset_id, path in REFERENCES.items()}}
    OUT.write_text(json.dumps({'source': source, 'datasets': datasets}, ensure_ascii=False, indent=1, default=str) + '\n')
    print(OUT, commit)


if __name__ == '__main__':
    main()
