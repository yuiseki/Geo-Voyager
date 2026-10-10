"""Benchmark goals for measuring repair success on naturally occurring failures.

Each oracle runs in its own sandbox through the same Gateway but is never shown to the
Planner, Generator, Repairer or Critic. A judge compares the final Observation text with
the oracle output.
"""
from dataclasses import dataclass
import json
import re
from functools import partial
from typing import Callable


@dataclass(frozen=True)
class BenchGoal:
    id: str
    text: str
    oracle_code: str
    judge: Callable[[str, dict], bool]
    # Services or datasets a correct plan has to declare in some Intent.
    required: tuple[str, ...] = ()
    # Relation id of the ward the Goal is about, when an intermediate step has to find it.
    target_relation: int | None = None


def normalize_text(text: str) -> str:
    """json.dumps escapes non-ASCII as \\uXXXX; a judge has to see the characters."""
    return re.sub(r'\\u([0-9a-fA-F]{4})', lambda match: chr(int(match.group(1), 16)), text)


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r'\d+(?:\.\d+)?', text.replace(',', '')))


def judge_count(final_text: str, oracle: dict) -> bool:
    return str(oracle['count']) in numbers_in(normalize_text(final_text))


def judge_max(final_text: str, oracle: dict) -> bool:
    text = normalize_text(final_text)
    return oracle['name'] in text and str(oracle['count']) in numbers_in(text)


# The romaji of the wards the comparison Goals name, so that an answer in English names the same winner.
WARD_ROMAJI = {'渋谷区': 'shibuya', '新宿区': 'shinjuku', '港区': 'minato', '台東区': 'taito', '世田谷区': 'setagaya'}


def _names_of(label: str) -> set[str]:
    names = {label.lower()}
    if label in WARD_ROMAJI:
        names |= {label.removesuffix('区'), WARD_ROMAJI[label]}
    return names


def judge_winner(final_text: str, oracle: dict, labels: tuple[str, str]) -> bool:
    """A comparison is answered when the larger side is named together with its count. A ward may be named in
    Japanese, without 区, or in romaji."""
    text = normalize_text(final_text).lower()
    winner = max(range(2), key=lambda index: oracle['counts'][index])
    return any(name in text for name in _names_of(labels[winner])) and str(oracle['counts'][winner]) in numbers_in(text)


def judge_close(final_text: str, oracle: dict, tolerance: float = 0.02) -> bool:
    return any(abs(float(n) - oracle['value']) <= tolerance * abs(oracle['value'])
               for n in numbers_in(normalize_text(final_text)))


def judge_abs(final_text: str, oracle: dict, tolerance: float = 0.0005) -> bool:
    return any(abs(float(n) - oracle['value']) <= tolerance for n in numbers_in(final_text))


def judge_latlon(final_text: str, oracle: dict, tolerance: float = 0.002) -> bool:
    found = [float(n) for n in numbers_in(final_text)]
    return (any(abs(n - oracle['lat']) <= tolerance for n in found)
            and any(abs(n - oracle['lon']) <= tolerance for n in found))


def judge_strings(final_text: str, oracle: dict) -> bool:
    text = normalize_text(final_text)
    return all(value in text for value in oracle['values'])


def overpass_count(key: str, value: str, relation: int) -> str:
    query = f'[out:json][timeout:12];nwr["{key}"="{value}"](area:{relation + 3600000000});out count;'
    return ('from geo_voyager.control_primitives import call_service\nimport json\n'
            f'q = {query!r}\n'
            'r = json.loads(call_service("overpass", path="/api/interpreter", body=q, content_type="text/plain"))\n'
            'assert not r.get("remark") and len(r["elements"]) == 1\n'
            'print(json.dumps({"count": int(r["elements"][0]["tags"]["total"])}))')


# Relation ids confirmed against the self-hosted Nominatim (osm_type=relation).
WARDS = {'渋谷区': 1759477, '新宿区': 1758858, '港区': 1761717, '台東区': 1758888, '世田谷区': 1759474}


def judge_all_counts(final_text: str, oracle: dict) -> bool:
    return all(str(n) in numbers_in(final_text) for n in oracle['counts'])


def overpass_counts(pairs: list[tuple[str, str, int]]) -> str:
    return ('from geo_voyager.control_primitives import call_service\nimport json\n'
            f'pairs = {pairs!r}\ncounts = []\n'
            'for key, value, relation in pairs:\n'
            '    q = f\'[out:json][timeout:12];nwr["{key}"="{value}"](area:{relation + 3600000000});out count;\'\n'
            '    r = json.loads(call_service("overpass", path="/api/interpreter", body=q, content_type="text/plain"))\n'
            '    assert not r.get("remark") and len(r["elements"]) == 1\n'
            '    counts.append(int(r["elements"][0]["tags"]["total"]))\n'
            'print(json.dumps({"count": counts[0], "counts": counts}))')


def feature_goal(id: str, ward: str, key: str, value: str, label: str) -> BenchGoal:
    return BenchGoal(id, f'{ward}の {key}={value}（{label}）の OSM 地物数を求める。',
                     overpass_counts([(key, value, WARDS[ward])]), judge_count,
                     required=('overpass',), target_relation=WARDS[ward])


def sandbox(*lines: str) -> str:
    return '\n'.join(lines)


GEOSPARQL_WARDS = (
    'from geo_voyager.control_primitives import call_service\nimport json\n'
    'PREFIX = "PREFIX gs: <https://yuiseki.net/geosparql/schema#> '
    'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "\n'
    'def select(body):\n'
    '    r = json.loads(call_service("yuisekin-geosparql", path="/geo/sparql", params={"query": PREFIX + body}))\n'
    '    return r["results"]["bindings"]\n'
    'rows = select("SELECT ?label ?rel WHERE { ?w a gs:Ward ; rdfs:label ?label ; gs:osmRelation ?rel . '
    'FILTER(LANG(?label) = \\"ja\\") }")\n'
    'wards = [(r["label"]["value"], int(r["rel"]["value"].rsplit("/", 1)[-1])) for r in rows]\n'
    'assert len(wards) == 23 and len({w[0] for w in wards}) == 23\n')


def taginfo_value(value: str) -> str:
    return sandbox(
        'from geo_voyager.control_primitives import call_service', 'import json',
        'r = json.loads(call_service("taginfo", path="/api/4/key/values", '
        'params={"key": "cuisine", "page": "1", "rp": "200", "sortname": "count", "sortorder": "desc"}))',
        f'row = [x for x in r["data"] if x["value"] == {value!r}][0]',
        'alt = json.loads(call_service("taginfo", path="/api/4/search/by_value", '
        f'params={{"query": {value!r}, "rp": "50", "sortname": "count_all", "sortorder": "desc"}}))',
        f'alt_row = [x for x in alt["data"] if x["key"] == "cuisine" and x["value"] == {value!r}][0]',
        'assert row["count"] == alt_row["count_all"], (row, alt_row)',
        'print(json.dumps({"count": row["count"]}))')


def valhalla_route(costing: str, field: str, divisor: int) -> str:
    return sandbox(
        'from geo_voyager.control_primitives import call_service', 'import json',
        'q = {"locations": [{"lat": 35.6580, "lon": 139.7016}, {"lat": 35.6896, "lon": 139.7006}],',
        f'     "costing": "{costing}", "units": "kilometers"}}',
        'r = json.loads(call_service("valhalla", path="/route", body=json.dumps(q), content_type="application/json"))',
        f'print(json.dumps({{"value": r["trip"]["summary"]["{field}"] / {divisor}}}))')


def nominatim_search(query: str, extract: str) -> str:
    return sandbox(
        'from geo_voyager.control_primitives import call_service', 'import json',
        f'r = json.loads(call_service("nominatim", path="/search", params={{"q": {query!r}, "format": "jsonv2", "limit": "1"}}))',
        'top = r[0]', extract)


def dataset_oracle(setup: str, query: str, output: str) -> str:
    return sandbox('from geo_voyager.control_primitives import connect_duckdb, load_admin_units, load_stations',
                   'import json', 'con = connect_duckdb()', setup, query, output)


ADMIN = "load_admin_units('yuiseki/jp-admin-2026-09', con, area='東京都23区')"
STATIONS = "load_stations('yuiseki/ekidata-jp', con)"

GOALS = [
    # Overpass
    feature_goal('cafe_shibuya', '渋谷区', 'amenity', 'cafe', 'カフェ'),
    feature_goal('ramen_shinjuku', '新宿区', 'cuisine', 'ramen', 'ラーメン'),
    feature_goal('hospital_minato', '港区', 'amenity', 'hospital', '病院'),
    feature_goal('hotel_taito', '台東区', 'tourism', 'hotel', 'ホテル'),
    feature_goal('library_setagaya', '世田谷区', 'amenity', 'library', '図書館'),
    BenchGoal('cafe_vs_restaurant_shibuya',
              '渋谷区で amenity=cafe と amenity=restaurant の OSM 地物数をそれぞれ求め、どちらが多いかを示す。',
              overpass_counts([('amenity', 'cafe', WARDS['渋谷区']), ('amenity', 'restaurant', WARDS['渋谷区'])]),
              partial(judge_winner, labels=('cafe', 'restaurant')), required=('overpass',),
              target_relation=WARDS['渋谷区']),
    # Two targets in one Goal: the second count can reuse what the first one taught.
    BenchGoal('cafe_shibuya_vs_shinjuku',
              '渋谷区と新宿区の amenity=cafe の OSM 地物数をそれぞれ求め、どちらが多いかを示す。',
              overpass_counts([('amenity', 'cafe', WARDS['渋谷区']), ('amenity', 'cafe', WARDS['新宿区'])]),
              partial(judge_winner, labels=('渋谷区', '新宿区')), required=('overpass',)),
    # Taginfo
    BenchGoal('tag_sushi_count', 'Taginfo で cuisine=sushi のタグの使用数（OSM 全体の件数）を求める。',
              taginfo_value('sushi'), judge_count, required=('taginfo',)),
    BenchGoal('tag_top3_cuisine', 'Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。',
              sandbox('from geo_voyager.control_primitives import call_service', 'import json',
                      'r = json.loads(call_service("taginfo", path="/api/4/key/values", '
                      'params={"key": "cuisine", "page": "1", "rp": "3", "sortname": "count", "sortorder": "desc"}))',
                      'print(json.dumps({"values": [x["value"] for x in r["data"]]}))'),
              judge_strings, required=('taginfo',)),
    BenchGoal('tag_ramen_vs_sushi', 'Taginfo で cuisine=ramen と cuisine=sushi の使用数をそれぞれ求め、どちらが多いかを示す。',
              sandbox('from geo_voyager.control_primitives import call_service', 'import json',
                      'r = json.loads(call_service("taginfo", path="/api/4/key/values", '
                      'params={"key": "cuisine", "page": "1", "rp": "200", "sortname": "count", "sortorder": "desc"}))',
                      'by = {x["value"]: x["count"] for x in r["data"]}',
                      'print(json.dumps({"counts": [by["ramen"], by["sushi"]]}))'),
              partial(judge_winner, labels=('ramen', 'sushi')), required=('taginfo',)),
    # Nominatim
    BenchGoal('nom_shibuya_relation', 'Nominatim で「渋谷区」（東京都）の OSM relation ID を求める。',
              nominatim_search('渋谷区 東京都', 'print(json.dumps({"count": top["osm_id"]}))'),
              judge_count, required=('nominatim',)),
    BenchGoal('nom_setagaya_south', 'Nominatim で「世田谷区」（東京都）の境界ボックスの最南端の緯度を求める。',
              nominatim_search('世田谷区 東京都', 'print(json.dumps({"value": float(top["boundingbox"][0])}))'),
              judge_abs, required=('nominatim',)),
    BenchGoal('nom_tokyo_tower', 'Nominatim で「東京タワー」の緯度と経度を求める。',
              nominatim_search('東京タワー', 'print(json.dumps({"lat": float(top["lat"]), "lon": float(top["lon"])}))'),
              judge_latlon, required=('nominatim',)),
    # Valhalla
    BenchGoal('route_auto_km',
              '緯度35.6580 経度139.7016 から 緯度35.6896 経度139.7006 への自動車（auto）の経路距離をキロメートルで求める。',
              valhalla_route('auto', 'length', 1), judge_close, required=('valhalla',)),
    BenchGoal('route_walk_minutes',
              '緯度35.6580 経度139.7016 から 緯度35.6896 経度139.7006 への徒歩（pedestrian）の所要時間を分で求める。',
              valhalla_route('pedestrian', 'time', 60),
              lambda text, oracle: judge_close(text, oracle, 0.05), required=('valhalla',)),
    # GeoSPARQL
    BenchGoal('sparql_ward_count', 'YuisekinGeoSPARQL に登録された東京23区（gs:Ward）の区の数を求める。',
              GEOSPARQL_WARDS + 'print(json.dumps({"count": len(wards)}))', judge_count,
              required=('yuisekin-geosparql',)),
    BenchGoal('sparql_min_relation_ward',
              'YuisekinGeoSPARQL の東京23区のうち、OSM relation の数値 ID が最小の区の日本語名とその ID を求める。',
              GEOSPARQL_WARDS + 'name, rel = min(wards, key=lambda w: w[1])\nprint(json.dumps({"name": name, "count": rel}))',
              judge_max, required=('yuisekin-geosparql',)),
    BenchGoal('sparql_four_char_wards',
              'YuisekinGeoSPARQL の東京23区のうち、日本語名（「区」を含む）が4文字の区の数を求める。',
              GEOSPARQL_WARDS + 'print(json.dumps({"count": sum(1 for w in wards if len(w[0]) == 4)}))',
              judge_count, required=('yuisekin-geosparql',)),
    # Datasets
    BenchGoal('ward_pop_max', '東京23区のうち人口が最も多い区の名前と人口を求める。',
              dataset_oracle(f'rel = {ADMIN}', "code, name, population = rel.order('population DESC').limit(1).fetchone()",
                             'print(json.dumps({"name": name, "count": int(population)}))'),
              judge_max, required=('yuiseki/jp-admin-2026-09',)),
    BenchGoal('ward_pop_total', '東京23区の人口の合計を求める。',
              dataset_oracle(f'rel = {ADMIN}', "total = rel.aggregate('sum(population)').fetchone()[0]",
                             'print(json.dumps({"count": int(total)}))'),
              judge_count, required=('yuiseki/jp-admin-2026-09',)),
    BenchGoal('stations_count', '駅データに収録されている駅の全レコード数を求める。絞り込みや重複排除はしない。',
              dataset_oracle(f'rel = {STATIONS}', "n = rel.aggregate('count(*)').fetchone()[0]",
                             'print(json.dumps({"count": int(n)}))'),
              judge_count, required=('yuiseki/ekidata-jp',)),
    BenchGoal('stations_northmost', '駅データのうち最も北（緯度が最大）にある駅の名前を求める。',
              dataset_oracle(f'rel = {STATIONS}', "name = rel.order('latitude DESC').limit(1).fetchone()[0]",
                             'print(json.dumps({"values": [name]}))'),
              judge_strings, required=('yuiseki/ekidata-jp',)),
]
