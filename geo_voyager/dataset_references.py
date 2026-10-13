"""What the Planner is told about each dataset the sandbox can read.

The facts are the dataset's reference in GeoAI-skills (the How-to Graph), copied with its commit into
dataset_references.json by scripts/sync_dataset_references.py: what a row is, the keys it does not have, what the
main columns mean, all measured on the data. read_table returns every column under these names (ADR 0010). What the
primitives add (an area read at once, the zonal sums of the population grid) is said here.
"""
import json
from pathlib import Path

_DATA = json.loads((Path(__file__).with_name('dataset_references.json')).read_text(encoding='utf-8'))
SOURCE = _DATA['source']

# The table of each dataset the Planner is told about: the one most Goals read.
_MAIN_TABLE = {
    'yuiseki/jp-admin-2026-09': 'municipalities',
    'yuiseki/ekidata-jp': 'station',
    'yuiseki/worldpop-jp-2026-01': 'population_100m_2020',
}
_NOTES = {
    'yuiseki/jp-admin-2026-09': '東京23区の23区は1回で読める。',
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
    return text + _NOTES.get(dataset_id, '')
