"""Benchmark goals for measuring repair success on naturally occurring failures.

Each oracle runs in its own sandbox through the same Gateway but is never shown to the
Planner, Generator, Repairer or Critic. A judge compares the final Observation text with
the oracle output.
"""
from dataclasses import dataclass
import json
import re
from typing import Callable


@dataclass(frozen=True)
class BenchGoal:
    id: str
    text: str
    oracle_code: str
    judge: Callable[[str, dict], bool]


def numbers_in(text: str) -> set[str]:
    return set(re.findall(r'\d+(?:\.\d+)?', text.replace(',', '')))


def judge_count(final_text: str, oracle: dict) -> bool:
    return str(oracle['count']) in numbers_in(final_text)


def judge_max(final_text: str, oracle: dict) -> bool:
    return oracle['name'] in final_text and str(oracle['count']) in numbers_in(final_text)


def judge_close(final_text: str, oracle: dict, tolerance: float = 0.02) -> bool:
    return any(abs(float(n) - oracle['value']) <= tolerance * oracle['value']
               for n in numbers_in(final_text))


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
                     overpass_counts([(key, value, WARDS[ward])]), judge_count)


GOALS = [
    feature_goal('cafe_shibuya', '渋谷区', 'amenity', 'cafe', 'カフェ'),
    feature_goal('ramen_shinjuku', '新宿区', 'cuisine', 'ramen', 'ラーメン'),
    feature_goal('hospital_minato', '港区', 'amenity', 'hospital', '病院'),
    feature_goal('hotel_taito', '台東区', 'tourism', 'hotel', 'ホテル'),
    feature_goal('library_setagaya', '世田谷区', 'amenity', 'library', '図書館'),
    BenchGoal('cafe_vs_restaurant_shibuya',
              '渋谷区で amenity=cafe と amenity=restaurant の OSM 地物数をそれぞれ求め、どちらが多いかを示す。',
              overpass_counts([('amenity', 'cafe', WARDS['渋谷区']), ('amenity', 'restaurant', WARDS['渋谷区'])]),
              judge_all_counts),
]
