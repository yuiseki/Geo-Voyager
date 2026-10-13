"""What the Planner is told about each dataset the sandbox can read.

The facts are the dataset's reference in GeoAI-skills (the How-to Graph), copied with its commit into
dataset_references.json by scripts/sync_dataset_references.py: what a row is, the keys it does not have, what the
columns mean, all measured on the data. Only the columns the sandbox's primitive returns are shown, under the names it
gives them: a column the dataset has but the primitive does not return would only lead to an Intent no code can
answer. What the primitive adds (an area read at once, the zonal sums of the population grid) is said here.
"""
import json
from pathlib import Path
import re

from .control_primitives.load_admin_units import COLUMNS as ADMIN_COLUMNS
from .control_primitives.load_stations import COLUMNS as STATION_COLUMNS

_DATA = json.loads((Path(__file__).with_name('dataset_references.json')).read_text(encoding='utf-8'))
SOURCE = _DATA['source']

# The table of the reference each primitive reads, and the primitive's projection of it.
_READ = {
    'yuiseki/jp-admin-2026-09': ('municipalities', ADMIN_COLUMNS),
    'yuiseki/ekidata-jp': ('station', STATION_COLUMNS),
    'yuiseki/worldpop-jp-2026-01': ('population_100m_2020', ''),
}
_NOTES = {
    'yuiseki/jp-admin-2026-09': '東京23区の23区は1回で読める。',
    'yuiseki/worldpop-jp-2026-01': (
        '実行環境で読めるのは2020年の100m総人口（constrained）だけで、sum_population_grid が、渡した区域ごとに画素を足した'
        '推計人口を返す。Goal が WorldPop・推計を名指ししない人口は、yuiseki/jp-admin-2026-09 の国勢調査人口を使う。'),
}


def _items(projection: str) -> list[str]:
    """The comma-separated items of a SELECT list, not splitting inside parentheses."""
    items, depth, current = [], 0, ''
    for char in projection:
        depth += (char == '(') - (char == ')')
        if char == ',' and depth == 0:
            items.append(current.strip()); current = ''
        else:
            current += char
    return [item for item in items + [current.strip()] if item]


def _projection(dataset_id: str) -> list[tuple[str, str, bool]]:
    """(column in the dataset, name the code sees, whether the primitive changes the value) for each item."""
    out = []
    for item in _items(_READ[dataset_id][1]):
        alias = re.search(r'\s+AS\s+(\w+)$', item, re.IGNORECASE)
        changed = '(' in item
        source = re.search(r'\w+', item.split('(', 1)[1] if changed else item).group()
        out.append((source, alias.group(1) if alias else source, changed))
    return out


def readable_columns(dataset_id: str) -> dict[str, str]:
    """The dataset's columns the primitive returns: {column in the dataset: name the code sees}."""
    return {source: name for source, name, _ in _projection(dataset_id)}


def planner_text(dataset_id: str) -> str:
    reference = _DATA['datasets'][dataset_id]
    table_name, _ = _READ[dataset_id]
    table = next(table for table in reference['tables'] if table['name'] == table_name)
    meanings = {key['column']: key['meaning'] for key in table.get('join_keys', [])}
    meanings.update({column['name']: column['meaning'] for column in table.get('columns', [])})
    text = f"{reference['description']} 1 行は{table['grain']}。"
    if table.get('no_key'):
        text += '持たないキー: ' + '、'.join(f"{key['name']}（{key['note']}）" for key in table['no_key']) + '。'
    projection = _projection(dataset_id)
    if projection:
        # A value the primitive changes (the boundaries' CRS) is not what the reference describes: name only.
        text += '読める列: ' + '、'.join(f'{name}（{meanings[column]}）' if column in meanings and not changed else name
                                     for column, name, changed in projection) + '。'
    return text + _NOTES.get(dataset_id, '')
