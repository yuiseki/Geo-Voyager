"""The tables an Intent's datasets offer, as the Generator and the repair read them (ADR 0010).

Made from the dataset references copied from GeoAI-skills (what a row is, the keys, the keys a table lacks, what
the main columns mean) and the schema measured at sync time (every column and its type), so a table becomes usable
by syncing its reference, without writing its contract here. Only the datasets the Intent declares are shown: the
prompt has 8192 tokens in all.
"""
import json
from pathlib import Path

from ..docker_sandbox import DEFAULT_PROFILE

_DATA = json.loads((Path(__file__).parents[1] / 'dataset_references.json').read_text(encoding='utf-8'))

# Areas a Goal names, as conditions on the boundaries' columns. Measured on jp-admin-2026-09 (2026-10-13): 23 rows,
# code5 13101 to 13123, population 9,733,276.
NAMED_AREAS = {'東京23区': "pref_code = '13' AND name LIKE '%区'"}
_AREAS_OF = {'yuiseki/jp-admin-2026-09': ('municipalities', NAMED_AREAS)}
_SHORT_TYPES = {'VARCHAR': 'VARCHAR', 'INTEGER': 'INTEGER', 'BIGINT': 'BIGINT', 'DOUBLE': 'DOUBLE'}


def _table_text(dataset_id: str, table: dict) -> str:
    meanings = {key['column']: key['meaning'] for key in table.get('join_keys', [])}
    meanings.update({column['name']: column['meaning'] + (f"。欠損: {column['missing']}" if column.get('missing') else '')
                     + (f"。注意: {column['note']}" if column.get('note') else '')
                     for column in table.get('columns', [])})
    # A geometry column's meaning is left out (the type says it), unless it carries a note on how to use it.
    noted = {column['name'] for column in table.get('columns', []) if column.get('note')}
    lines = [f'read_table(connection, "{dataset_id}", "{table["name"]}"): 1 行は{table["grain"]}。']
    if table.get('id'):
        lines[0] += f'ID: {", ".join(table["id"])}。'
    if table.get('join_keys'):
        lines.append('  結合キー: ' + '、'.join(f'{key["column"]}（→ {", ".join(key.get("joins", []))}'
                                               + (f'。{key["cast"]}' if key.get('cast') else '') + '）'
                                               for key in table['join_keys']))
    if table.get('no_key'):
        lines.append('  持たないキー: ' + '、'.join(f'{key["name"]}（{key["note"]}）' for key in table['no_key']))
    columns = table['schema']['columns']
    lines.append('  列: ' + ', '.join(f'{name} {"GEOMETRY" if kind.startswith("GEOMETRY") else kind}'
                                     for name, kind in columns))
    described = [f'{name}（{meanings[name]}）' for name, kind in columns if name in meanings and (not kind.startswith('GEOMETRY') or name in noted)]
    if described:
        lines.append('  列の意味: ' + '、'.join(described))
    split_by = table['schema'].get('split_by')
    if split_by:
        lines.append(f'  読み方: 行は {split_by[0]} ごとに {table["schema"]["row_groups"]} の塊に分けて保存されている。'
                     f'{split_by[0]} の条件を付けると、その塊だけを読む。付けないと全部を読み、実行の上限 {DEFAULT_PROFILE.timeout} 秒を超えうる')
    area_table, areas = _AREAS_OF.get(dataset_id, (None, {}))
    if table['name'] == area_table:
        lines.append('  名前のついた地域: ' + '、'.join(f'{name}: filter("{condition}")' for name, condition in areas.items()))
    return '\n'.join(lines)


def table_contract(dataset_ids) -> str:
    texts = []
    for dataset_id in dataset_ids:
        reference = _DATA['datasets'].get(dataset_id)
        if reference is None:
            continue
        for table in reference['tables']:
            if 'schema' in table:
                texts.append(_table_text(dataset_id, table))
            else:
                texts.append(f'{dataset_id} の {table["name"]} はラスタで、表として読まない（1 画素は{table["grain"]}）。'
                             'sum_population_grid(connection, zones) が、zones（geometry 列を持つ relation）の区域ごとに画素を足す。')
    if texts:
        texts.append('geometry は OGC:CRS84（read_table がそろえる）。2 つの表は ST_Within などで空間結合できる。')
    return '\n'.join(texts)
