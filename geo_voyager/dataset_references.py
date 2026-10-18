"""What the Planner is told about each dataset the sandbox can read.

The facts are the dataset's reference in GeoAI-master-skills (the How-to Graph), copied with its commit into
dataset_references.json by scripts/sync_dataset_references.py: what a row is, the keys it does not have, what the
main columns mean, all measured on the data. read_table returns every column under these names (ADR 0010). What the
primitives add (an area read at once, the zonal sums of the population grid) is said here.
"""
import json
from pathlib import Path
import re

_DATA = json.loads((Path(__file__).with_name('dataset_references.json')).read_text(encoding='utf-8'))
SOURCE = _DATA['source']
REFERENCED = frozenset(_DATA['datasets'])

# The table of each dataset the Planner is told about: the one most Goals read.
_MAIN_TABLE = {
    'yuiseki/jp-admin-2026-09': 'municipalities',
    'yuiseki/ekidata-jp': 'station',
    'yuiseki/worldpop-jp-2026-01': 'population_100m_2020',
    'yuiseki/worldbank-wdi': 'data',
    'yuiseki/natural-earth': 'ne_10m_admin_0_countries',
    'yuiseki/ksj-l01-land-price': 'land_price',
    'yuiseki/osm-tokyo23-src-2026-08': 'planet_osm_polygon',
}
_NOTES = {
    'yuiseki/osm-tokyo23-src-2026-08': ('read_table は way を OGC:CRS84 の経度、緯度に直して返す（元の EPSG:3857 のメートルのままにはしない）。'
                                        '23 区の中で閉じる OSM の問いは、Overpass よりこの表のほうが軽い。'),
    'yuiseki/jp-admin-2026-09': ('東京23区の23区は1回で読める。区や市区町村の中心点は、この Dataset の代表点 rep_lon と rep_lat を使う。'
                                 'Goal が OSM を名指ししないとき、中心点を Overpass で求めない。'),
    'yuiseki/worldpop-jp-2026-01': (
        '実行環境で読めるのは2020年の100m総人口（constrained）だけで、sum_population_grid が、渡した区域ごとに画素を足した'
        '推計人口を返す。Goal が WorldPop・推計を名指ししない人口は、yuiseki/jp-admin-2026-09 の国勢調査人口を使う。'),
}


def planner_text(dataset_id: str) -> str:
    reference = _DATA['datasets'][dataset_id]
    table = next(table for table in reference['tables'] if table['name'] == _MAIN_TABLE[dataset_id])
    meanings = {key['column']: key['meaning'] for key in table.get('join_keys', [])}
    meanings.update({column['name']: column['meaning'] for column in table.get('columns', [])})
    text = f"{reference['description']} 1 行は{table['grain']}。"
    if table.get('no_key'):
        text += '持たないキー: ' + '、'.join(f"{key['name']}（{key['note']}）" for key in table['no_key']) + '。'
    if meanings:
        # read_table returns every column under the reference's name (ADR 0010); these are the main ones.
        text += '主な列: ' + '、'.join(f'{name}（{meaning}）' for name, meaning in meanings.items()
                                    if name != 'geometry') + '。'
    # A column's note says how to use it (jp-admin's geometry: touching pairs are taken with ST_Intersects), as the
    # Generator's table text does (geo_voyager.contracts.tables).
    notes = [f"{key['column']}: {key['note']}" for key in table.get('join_keys', []) if key.get('note')]
    notes += [f"{column['name']}: {column['note']}" for column in table.get('columns', []) if column.get('note')]
    if notes:
        text += '注意: ' + ' '.join(notes) + '。'
    if table.get('read_chosen_by'):
        # The reference describes every year, the sandbox reads one (scripts/sync_dataset_references.py READ_AS).
        placeholder, value = table['read_chosen_by'].removeprefix('Geo-Voyager: ').split(' = ')
        text += f'実行環境で読めるのは {placeholder} が {value} の表だけで、ほかの {placeholder} は読めない。'
    return text + _NOTES.get(dataset_id, '')


def _used(name: str, code: str) -> bool:
    return re.search(rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])', code) is not None


def critic_text(dataset_id: str, code: str) -> str:
    """What the Critic is told about a dataset the code read: what a row of each table the code names is, and what
    the columns it uses mean. Told the description alone, the Critic failed code that kept the rows with ward IS NULL
    for not leaving out the wards' rows; that ward is empty on the parent city's row is in the column's meaning."""
    reference = _DATA['datasets'][dataset_id]
    tables = ([table for table in reference['tables'] if re.search(rf'["\']{re.escape(table["name"])}["\']', code)]
              or [table for table in reference['tables'] if table['name'] == _MAIN_TABLE[dataset_id]])
    text = ''
    for table in tables:
        meanings = {key['column']: key['meaning'] for key in table.get('join_keys', [])}
        meanings.update({column['name']: column['meaning'] for column in table.get('columns', [])})
        notes = {key['column']: key['note'] for key in table.get('join_keys', []) if key.get('note')}
        notes.update({column['name']: column['note'] for column in table.get('columns', []) if column.get('note')})
        # As the Generator is told (contracts.tables): told only that way is in metres, the Critic failed code that
        # measured it in the longitude and latitude read_table returns.
        meanings.update({column['name']: 'read_table が OGC:CRS84 の経度、緯度に直して返す。元は EPSG:3857 のメートル'
                         for column in table.get('columns', []) if 'EPSG:3857' in column.get('type', '')})
        used = [name for name in meanings if _used(name, code)]
        text += f" {table['name']} の 1 行は{table['grain']}。"
        if used:
            text += 'コードが使う列: ' + '、'.join(
                f'{name}（{meanings[name]}' + (f'。{notes[name]}' if name in notes else '') + '）' for name in used) + '。'
    return text.strip()
