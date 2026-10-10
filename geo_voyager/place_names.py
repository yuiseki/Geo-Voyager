"""Names of the places the Goals are about, in the forms a function name can carry them.

A Skill is a part that later Intents call with other arguments. A function named after the place of the current
Intent (count_hotels_in_taito, get_setagaya_relation_id) reads as being only for that place; in the carried-over
runs such names grew in number and were not reused. The 23 wards of Tokyo are listed in romaji, as a local model
writes them in identifiers.
"""
import re

WARD_ROMAJI = {
    '千代田区': 'chiyoda', '中央区': 'chuo', '港区': 'minato', '新宿区': 'shinjuku', '文京区': 'bunkyo',
    '台東区': 'taito', '墨田区': 'sumida', '江東区': 'koto', '品川区': 'shinagawa', '目黒区': 'meguro',
    '大田区': 'ota', '世田谷区': 'setagaya', '渋谷区': 'shibuya', '中野区': 'nakano', '杉並区': 'suginami',
    '豊島区': 'toshima', '北区': 'kita', '荒川区': 'arakawa', '板橋区': 'itabashi', '練馬区': 'nerima',
    '足立区': 'adachi', '葛飾区': 'katsushika', '江戸川区': 'edogawa',
}
# Short romaji that are also ordinary English or code words are left out: they would refuse ordinary names.
_TOO_COMMON = {'ota', 'kita', 'chuo', 'koto'}


def place_words_in(name: str, target_name: str | None = None) -> list[str]:
    """The place names a function name carries: a ward in romaji, or the ASCII form of the current target's name."""
    words = set(re.split(r'_+', name.lower()))
    places = {romaji for romaji in WARD_ROMAJI.values() if romaji not in _TOO_COMMON}
    if target_name:
        romaji = WARD_ROMAJI.get(target_name.split(',')[0].strip())
        if romaji:
            places.add(romaji)
        places |= {part for part in re.split(r'[^a-z0-9]+', target_name.lower()) if len(part) > 2}
    return sorted(words & places)
