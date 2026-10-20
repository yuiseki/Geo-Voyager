"""The tables an Intent's datasets offer, as the Generator and the repair read them (ADR 0010).

Made from the dataset references copied from GeoAI-master-skills (what a row is, the keys, the keys a table lacks, what
the main columns mean) and the schema measured at sync time (every column and its type), so a table becomes usable
by syncing its reference, without writing its contract here. Only the datasets the Intent declares are shown: the
prompt has 8192 tokens in all.
"""
import json
import re
from pathlib import Path

import duckdb

from ..docker_sandbox import DEFAULT_PROFILE

_DATA = json.loads((Path(__file__).parents[1] / 'dataset_references.json').read_text(encoding='utf-8'))

# Areas a Goal names, as conditions on the boundaries' columns. Measured on jp-admin-2026-09 (2026-10-13): 23 rows,
# code5 13101 to 13123, population 9,733,276.
NAMED_AREAS = {'東京23区': "pref_code = '13' AND name LIKE '%区'"}
_AREAS_OF = {'yuiseki/jp-admin-2026-09': ('municipalities', NAMED_AREAS)}
# How to measure on longitude, latitude in this DuckDB (1.5.6), measured 2026-10-15. Degrees are not metres: a
# circle of 1/111 degree around Tokyo is 2.54 km², not 3.14 (GeoAI-master-skills, spatial-data-integration, crs-and-datum).
MEASURING = ('座標は経度、緯度の度で、面積と距離と円は度のまま測らない。'
             "面積は ST_Area(ST_Transform(geometry, 'OGC:CRS84', 'EPSG:6933'))（m²、等積）。"
             '2 点の距離は ST_Distance_Sphere(ST_FlipCoordinates(a), ST_FlipCoordinates(b))（m）。'
             'この DuckDB の ST_Distance_Sphere と *_Spheroid は緯度、経度の順を読み、入れ替えないと値が黙って誤る'
             '（東京と大阪の 396 km が 473 km、日本の面積が NaN）。'
             '半径 r m の円は、点ごとに UTM の帯を決め、移して ST_Buffer し、戻す: '
             "WITH z AS (SELECT *, 'EPSG:' || (32601 + CAST(floor((ST_X(geometry) + 180) / 6) AS INTEGER)) AS utm FROM 点) "
             "SELECT ..., ST_Transform(ST_Buffer(ST_Transform(geometry, 'OGC:CRS84', utm), r), utm, 'OGC:CRS84') AS geometry FROM z"
             '（東京で半径 998 m、面積 3.12 km²）。')
# The population grid, measured through the Gateway in the sandbox (2026-10-15). On GeoAI-master-skills' small task 11 the
# Generator looked for it in the files catalog with sex = 'total' and found no row, three runs out of three.
_RASTER_NOTES = {
    'yuiseki/worldpop-jp-2026-01': (
        'files の表は原本の目録で、cog_path は実行環境からは読めない。読めるのは 2020 年 100 m の総人口だけ'
        "（files では project = 'Population'、year = 2020、resolution = '100m' の 1 行。総人口の sex は NULL で、"
        "sex = 'total' で絞ると 0 行。その行の sum が全国の画素の合計 126,574,853）。"
        "画素を自分で読むときは rasterio.open('/vsicurl/' + dataset_url('yuiseki/worldpop-jp-2026-01'))"
        '（EPSG:4326、37,258 × 25,773 画素、512 画素の塊、欠損値 -99999）。全体を一度に読むと 3.8 GB で、'
        'メモリの上限 2 GB を超えて止められる。窓（rasterio.windows）で、塊ごとか区域ごとに読む。'),
}
_SHORT_TYPES = {'VARCHAR': 'VARCHAR', 'INTEGER': 'INTEGER', 'BIGINT': 'BIGINT', 'DOUBLE': 'DOUBLE'}


_NUMBERED = re.compile(r'(.+_)(\d+)')


def _column_runs(columns: list) -> list[str]:
    """Each column as `name TYPE`, with a run of columns that differ only by their number and share a type shown as one
    range: the land prices carry 148 original columns L01_001 to L01_148, whose meanings differ by year."""
    shown, index = [], 0
    while index < len(columns):
        name, kind = columns[index]
        kind = 'GEOMETRY' if kind.startswith('GEOMETRY') else kind
        numbered = _NUMBERED.fullmatch(name)
        end = index + 1
        while (numbered and end < len(columns) and columns[end][1] == columns[index][1]
               and (following := _NUMBERED.fullmatch(columns[end][0])) and following.group(1) == numbered.group(1)):
            end += 1
        if end - index >= 3:
            shown.append(f'{name}〜{columns[end - 1][0]} {kind}（{end - index} 列）')
        else:
            shown.extend(f'{other} {"GEOMETRY" if other_kind.startswith("GEOMETRY") else other_kind}'
                         for other, other_kind in columns[index:end])
        index = end
    return shown


def _columns_text(columns: list, shown_before: dict) -> str:
    """The columns, or, when a table shown before has nearly the same ones, that table's name and the difference: the
    four tables of osm2pgsql share about 70 columns, 6,667 characters when listed for each."""
    names = [name for name, _ in columns]
    for other, other_columns in shown_before.items():
        other_names = [name for name, _ in other_columns]
        added = [column for column in columns if column[0] not in other_names]
        missing = [name for name in other_names if name not in names]
        if len(added) + len(missing) <= 5:
            text = f'{other} と同じ'
            if added:
                text += '。ただし ' + ', '.join(_column_runs(added)) + ' がある'
            if missing:
                text += '。' + ', '.join(missing) + ' は無い'
            return text
    return ', '.join(_column_runs(columns))


def _table_text(dataset_id: str, table: dict, shown_before: dict | None = None) -> str:
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
                                               + (f'。{key["cast"]}' if key.get('cast') else '')
                                               + (f'。注意: {key["note"]}' if key.get('note') else '') + '）'
                                               for key in table['join_keys']))
    if table.get('no_key'):
        lines.append('  持たないキー: ' + '、'.join(f'{key["name"]}（{key["note"]}）' for key in table['no_key']))
    columns = table['schema']['columns']
    lines.append('  列: ' + _columns_text(columns, shown_before or {}))
    projected = [name for name, kind in columns if kind.startswith('GEOMETRY') and 'EPSG:3857' in kind]
    if projected:
        lines.append(f'  {", ".join(projected)} は read_table が OGC:CRS84 の経度、緯度に直して返す（元は EPSG:3857 のメートル）。'
                     'bbox は EPSG:3857 のメートルのまま')
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


# Words DuckDB does not read as a column's name unless it is quoted: natural = 'sand' is a syntax error, and four
# candidates of a Goal failed on it (explore 27). OSM's natural is the only such column of the datasets.
_KEYWORDS = frozenset(word for (word,) in duckdb.sql(
    "SELECT keyword_name FROM duckdb_keywords() WHERE keyword_category IN ('reserved', 'type_function')").fetchall())


def table_contract(dataset_ids) -> str:
    texts = []
    for dataset_id in dataset_ids:
        reference = _DATA['datasets'].get(dataset_id)
        if reference is None:
            continue
        shown = {}
        for table in reference['tables']:
            if 'schema' in table:
                texts.append(_table_text(dataset_id, table, shown))
                shown.setdefault(table['name'], table['schema']['columns'])
            else:
                texts.append(f'{dataset_id} の {table["name"]} はラスタで、表として読まない（1 画素は{table["grain"]}）。'
                             'sum_population_grid(connection, zones) が、zones（geometry 列を持つ relation）の区域ごとに画素を足す。'
                             + _RASTER_NOTES.get(dataset_id, ''))
    keywords = sorted({name for dataset_id in dataset_ids for table in _DATA['datasets'].get(dataset_id, {}).get('tables', [])
                       for name, _ in table.get('schema', {}).get('columns', []) if name.lower() in _KEYWORDS})
    if keywords:
        texts.append(f'{"、".join(keywords)} は SQL の予約語なので、SQL では '
                     + '、'.join(f'"{name}"' for name in keywords) + ' と二重引用符で囲む。')
    if texts:
        texts.append('geometry は OGC:CRS84（read_table がそろえる）。2 つの表は ST_Within などで空間結合できる。'
                     + MEASURING)
    return '\n'.join(texts)


# A tag read from the JSON of the tags that did not become columns: tags->>'power', tags->'power',
# json_extract_string(tags, '$.power').
_TAG_READ = re.compile(r"""\btags\s*->>?\s*'([^']+)'|json_extract(?:_string)?\s*\(\s*tags\s*,\s*'\$\.([^']+)'""")


def tag_column_problems(code: str, dataset_ids) -> list[str]:
    """The tags the code reads from tags although they have their own column, where tags never holds them: in
    explore 33 the code read tags->>'power' six times and found no power=plant area of the 7 the column has."""
    columns = {name for dataset_id in dataset_ids for table in _DATA['datasets'].get(dataset_id, {}).get('tables', [])
               for name in [column for column, _ in table.get('schema', {}).get('columns', [])]
               if any(column == 'tags' for column, _ in table['schema']['columns'])}
    read = dict.fromkeys(key for match in _TAG_READ.finditer(code) for key in match.groups() if key)
    return [f'{key} は表の列にあり、tags には入っていない（tags は列にならなかったタグだけ）。tags でなく "{key}" 列で読む'
            for key in read if key in columns]


_KIND = re.compile(r'[a-z_:]+=[a-z_:;-]+')
# A kind as an Intent may also write it, as a condition on the tags: tags->>'office'='government', office = 'government'.
_KIND_AS_CONDITION = re.compile(r"'?([a-z_:]+)'?\s*=\s*'([a-z_:;-]+)'")


def _kinds_named(text: str) -> list[str]:
    return _KIND.findall(text) + [f'{key}={value}' for key, value in _KIND_AS_CONDITION.findall(text)]


def point_only_problems(code: str, intent_text: str) -> list[str]:
    """The kinds the Intent names that have areas in the 23 wards, read from the points alone: shop=watches of 大田区
    (3 of 4 areas) and amenity=photo_booth of 港区 and 新宿区 (3 of 10) lost their areas (explores 37, 39)."""
    from ..ingredients import AREA_COUNTS, COUNTS
    if 'planet_osm_point' not in code or 'planet_osm_polygon' in code:
        return []
    kinds = dict.fromkeys(kind for kind in _kinds_named(intent_text) if AREA_COUNTS.get(kind))
    return [f'{kind} は 23 区の {COUNTS[kind]} 件のうち {AREA_COUNTS[kind]} 件が面で、planet_osm_point だけでは面の分が抜ける。'
            'planet_osm_polygon も読み、面は ST_PointOnSurface の点にして点と合わせる' for kind in kinds]


def polygon_only_problems(code: str, intent_text: str) -> list[str]:
    """The kinds the Intent names that are mostly points in the 23 wards, read from the areas alone: office=government
    of 杉並区 and 江戸川区 lost 273 of the 331 (explore 44). An Intent on the areas or ways of a kind asks for them; a
    ward's 境界面 is not one."""
    from ..ingredients import AREA_COUNTS, COUNTS
    asked = intent_text.replace('境界面', '').replace('市区町村面', '')
    if 'planet_osm_polygon' not in code or 'planet_osm_point' in code or re.search(r'面|(?<![A-Za-z])way(?![A-Za-z])|ウェイ', asked):
        return []
    kinds = dict.fromkeys(kind for kind in _kinds_named(intent_text) if COUNTS.get(kind, 0) > AREA_COUNTS.get(kind, 0))
    return [f'{kind} は 23 区の {COUNTS[kind]} 件のうち {COUNTS[kind] - AREA_COUNTS[kind]} 件が点で、planet_osm_polygon だけでは'
            '点の分が抜ける。planet_osm_point も読み、面は ST_PointOnSurface の点にして点と合わせる' for kind in kinds]
