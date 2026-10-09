import pytest

from geo_voyager.intent_text import api_details_in


@pytest.mark.parametrize('text,expected', [
    # an endpoint path the model made up, or one the services really have
    ('taginfo API /api/4/keys/cuisine/values を使い、上位3件を取得', ['/api/4/keys/cuisine/values']),
    ('Nominatim の /search で渋谷区を探す', ['/search']),
    ('Overpass の /api/interpreter に問い合わせる', ['/api/interpreter']),
    ('taginfo の key/values で値を取る', ['key/values']),
    ('search/by_value を呼ぶ', ['search/by_value']),
    ('https://taginfo.example.net/api/4/tags/list を取得する', ['/taginfo.example.net/api/4/tags/list']),
    # request parameters
    ('cuisine キーの値を limit=3 で取得する', ['limit=3']),
    ('sort=count と order=desc を指定して取得', ['sort=count', 'order=desc']),
    ('rp=3 と page=1 を付けて呼び出す', ['rp=3', 'page=1']),
    ('sortname=count_all, sortorder=desc で並べる', ['sortname=count_all', 'sortorder=desc']),
    ('/search?q=渋谷区&format=jsonv2 を呼ぶ', ['/search', 'q=渋谷区', 'format=jsonv2']),
    ('call_service で呼び出して取得する', ['call_service']),
    ('params={"key": "cuisine"} を渡す', ['params=']),
    # a query in the service's own language: the Generator writes it, the Planner does not
    ('クエリは [out:json][timeout:12];nwr["amenity"="cafe"](area:3601759477);out count; とする', ['[out:json]', 'nwr[', '(area:3601759477)', 'out count']),
    ('渋谷区 (relation_id=1759477) 内の amenity=cafe を nwr["amenity"="cafe"](area:3601759477) で数える', ['nwr[']),
    ('way["highway"="primary"] を取得する', ['way[']),
    ('SELECT ?ward WHERE { ?ward a gs:Ward } で区を取得する', ['SELECT ?', 'WHERE {']),
])
def test_api_paths_and_parameters_in_an_intent_are_found(text, expected):
    found = api_details_in(text)
    for item in expected:
        assert item in found, (item, found)


@pytest.mark.parametrize('text', [
    'cuisine キーの値を使用数の多い順に並べ、上位3つを求める',                 # what to find, not how
    '渋谷区の amenity=cafe の OSM 地物数を求める',                             # an OSM tag, not a parameter
    '新宿区の cuisine=ramen（ラーメン）の地物数を取得する',
    '港区の amenity=hospital の件数を取得する',
    '2026/10/09 時点の件数を比べる',
    '渋谷区/新宿区/港区 の人口を比べる',
    'A/B のどちらが多いか示す',
    '緯度35.6580 経度139.7016 から 緯度35.6896 経度139.7006 への自動車の経路距離を求める',
    '前段の渋谷区 (relation_id: 1759477) の件数を取得する',
    'Taginfo で cuisine=sushi のタグの使用数を求める',
    '港区, 東京都, 日本 の relation_id を取得する',
    'Taginfo で key="cuisine" の値を使用数の多い順に並べ、上位3つの値を取得する。',      # a tag key, written the way a key is
    'タグの key=cuisine に付く値を調べる',
    '渋谷区の area_id を relation_id から求めて amenity=cafe の件数を数える',       # the word area, not the clause
    '地区 (area) ごとに out of range の値を除いて集計する',
    'gs:Ward 型の区の一覧（名称と外部ID）を取得し、件数を数える',
    '',
])
def test_what_to_find_is_not_an_api_detail(text):
    assert api_details_in(text) == []


def test_each_detail_is_reported_once_in_the_order_it_appears():
    text = '/api/4/key/values で limit=3 を指定し、再度 /api/4/key/values で limit=3 を指定する'
    assert api_details_in(text) == ['/api/4/key/values', 'limit=3']


def test_a_parameter_name_inside_a_longer_word_is_not_a_parameter():
    assert api_details_in('timelimit=3 のような名前の記録を探す') == []
    assert api_details_in('prompt=3') == []
