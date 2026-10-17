"""Ingredients drawn at random for a Goal of exploration: kinds of things OSM maps, areas, measures, an indicator.

In exploration 11 (2026-10-15 to 17), 67 of the 72 Goals the curriculum proposed asked for a largest or smallest, and
most of them of the census's municipalities: it asks of the few things it thinks of first. A question such as the most
expensive tennis court of Tokyo pairs a kind of thing with a measure from another resource; drawn at random, such pairs
are put in front of it. The curriculum names the ingredients it used (geo_voyager.curriculum), which is checked
without a model.
"""
from dataclasses import dataclass
from pathlib import Path
import random

from .indicator_codes import INDICATORS


def _kinds() -> dict[str, str]:
    lines = Path(__file__).with_name('osm_kinds.tsv').read_text(encoding='utf-8').splitlines()
    rows = [line.split('\t') for line in lines if line and not line.startswith('#')][1:]
    return {tag: description for tag, _count, description in rows}


# The kinds of things OSM maps in the 23 wards, by their tag (scripts/sync_osm_kinds.py).
KINDS = _kinds()
# The 23 wards of Tokyo, where OpenStreetMap is read from a light frozen copy (yuiseki/osm-tokyo23-src-2026-08):
# Japan's is 6.5 GB, and the Overpass of the whole country is slow for questions on every lot or court.
AREAS = ('千代田区', '中央区', '港区', '新宿区', '文京区', '台東区', '墨田区', '江東区', '品川区', '目黒区', '大田区',
         '世田谷区', '渋谷区', '中野区', '杉並区', '豊島区', '北区', '荒川区', '板橋区', '練馬区', '足立区', '葛飾区',
         '江戸川区', '東京23区')
# What the resources can measure of a thing or a place, by a short name the curriculum writes back.
MEASURES = {
    '公示地価': 'その場所に近い標準地の公示価格（円/m²、2026 年。yuiseki/ksj-l01-land-price）',
    '地価の変動率': '標準地の対前年変動率（%、2026 年）',
    '駅までの直線距離': '最寄りの運行中の駅までの直線距離（yuiseki/ekidata-jp）',
    '駅までの道のり': '最寄りの駅までの道のりの距離か時間（valhalla、車か徒歩）',
    '周りの推計人口': '周り（たとえば半径 1 km）に住む推計人口（WorldPop の 100 m 格子）',
    '区の人口': '所在する区の人口か世帯数（2020 年国勢調査、yuiseki/jp-admin-2026-09）',
    '面積': 'OSM の面の面積（m²）',
    '件数': '範囲の中にある数',
    '名前': 'OSM の name',
    '位置': '位置そのもの（最も北、最も東、区の中心から最も遠い、など）',
}


@dataclass(frozen=True)
class Ingredients:
    kinds: tuple[str, ...]
    areas: tuple[str, ...]
    measures: tuple[str, ...]
    indicators: tuple[str, ...]

    def names(self) -> tuple[str, ...]:
        """What the curriculum may write back on its line 材料:."""
        return (*self.kinds, *self.areas, *self.measures, *self.indicators)

    def text(self) -> str:
        return ('対象（OSM のタグ）: ' + '、'.join(f'{kind}（{KINDS[kind][:80]}）' for kind in self.kinds) + '\n'
                + '範囲: ' + '、'.join(self.areas) + '\n'
                + '測る量: ' + '、'.join(f'{measure}（{MEASURES[measure]}）' for measure in self.measures) + '\n'
                + '世界銀行の指標: ' + '、'.join(f'{code}（{INDICATORS[code]}）' for code in self.indicators) + '\n')


def draw(rng: random.Random) -> Ingredients:
    return Ingredients(tuple(rng.sample(sorted(KINDS), 3)), tuple(rng.sample(AREAS, 2)),
                       tuple(rng.sample(sorted(MEASURES), 2)), tuple(rng.sample(sorted(INDICATORS), 1)))
