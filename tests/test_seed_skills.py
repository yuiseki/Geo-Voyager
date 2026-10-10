"""The six Skills the library starts with. Their purposes are those of the first Skills of v0.1.0, rewritten as
named functions that take the dataset and return values, so that other code can call them."""
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from geo_voyager.skill_library import SkillLibrary, link

LIBRARY = SkillLibrary(Path(__file__).resolve().parents[1] / 'skill_library')


@pytest.fixture
def primitives(monkeypatch):
    import geo_voyager.control_primitives as module
    connection = Mock()
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(module, 'connect_duckdb', Mock(return_value=context))
    loaders = {name: Mock() for name in ('load_admin_units', 'load_stations')}
    for name, loader in loaders.items():
        monkeypatch.setattr(module, name, loader)
    return connection, loaders


def run(call: str):
    namespace = {}
    exec(link(f'result = {call}', LIBRARY), namespace)
    return namespace['result']


def test_there_are_ten_seed_skills_and_each_says_what_it_does():
    names = LIBRARY.names()
    assert names == ['count_station_records', 'count_tag_in_area', 'get_relation_id', 'least_populous_area',
                     'most_populous_area', 'northernmost_station', 'route_summary', 'tag_usage_count',
                     'top_areas_by_population', 'total_population']
    assert all(LIBRARY.get(name).description for name in names)


@pytest.mark.parametrize('name,order', [('most_populous_area', 'population DESC, code5 ASC'),
                                        ('least_populous_area', 'population ASC, code5 ASC')])
def test_the_most_and_least_populous_area_are_ordered_and_returned(primitives, name, order):
    connection, loaders = primitives
    relation = loaders['load_admin_units'].return_value
    relation.order.return_value.limit.return_value.fetchone.return_value = ('13112', 'テスト区', 123)
    assert run(f'{name}("yuiseki/jp-admin-2026-09", area="東京都23区")') == {'code5': '13112', 'name': 'テスト区', 'population': 123}
    loaders['load_admin_units'].assert_called_once_with('yuiseki/jp-admin-2026-09', connection, area='東京都23区')
    relation.order.assert_called_once_with(order)


def test_the_top_areas_are_as_many_as_asked(primitives):
    _, loaders = primitives
    rows = [(f'1310{i}', f'区{i}', 100 - i) for i in range(3)]
    loaders['load_admin_units'].return_value.order.return_value.limit.return_value.fetchall.return_value = rows
    assert [item['name'] for item in run('top_areas_by_population("d", 3)')] == ['区0', '区1', '区2']
    with pytest.raises(ValueError, match='5 areas'):
        run('top_areas_by_population("d", 5)')


def test_the_total_population_and_the_station_count_are_aggregates(primitives):
    _, loaders = primitives
    loaders['load_admin_units'].return_value.aggregate.return_value.fetchone.return_value = (9_733_276,)
    loaders['load_stations'].return_value.aggregate.return_value.fetchone.return_value = (10_962,)
    assert run('total_population("d", area="東京都23区")') == 9_733_276
    assert run('count_station_records("s")') == 10_962


def test_the_northernmost_station(primitives):
    _, loaders = primitives
    loaders['load_stations'].return_value.order.return_value.limit.return_value.fetchone.return_value = ('稚内', 45.4, 141.6)
    assert run('northernmost_station("s")') == {'name': '稚内', 'latitude': 45.4, 'longitude': 141.6}


def test_no_seed_skill_holds_an_answer_or_a_url():
    for skill in LIBRARY.all():
        assert '世田谷' not in skill.code and '943664' not in skill.code and 'http' not in skill.code
        assert '1759477' not in skill.code and '459' not in skill.code



# ---- the service Seeds: the parameterised basic operations, as Voyager's control primitives

@pytest.fixture
def service(monkeypatch):
    import geo_voyager.control_primitives as module
    calls, replies = [], {}
    def call_service(service_id, *, path='', params=None, body=None, content_type=None):
        calls.append((service_id, path, params, body, content_type))
        return replies[(service_id, path)]
    monkeypatch.setattr(module, 'call_service', call_service)
    return calls, replies


def test_get_relation_id_uses_the_target_id_or_searches_for_a_relation(service):
    calls, replies = service
    assert run('get_relation_id({"name": "港区", "id_type": "relation_id", "id_value": "1761717"})') == {'name': '港区', 'relation_id': '1761717'}
    assert calls == []
    replies[('nominatim', '/search')] = '[{"osm_type": "node", "osm_id": 1}, {"osm_type": "relation", "osm_id": 1759477}]'
    assert run('get_relation_id({"name": "渋谷区"})') == {'name': '渋谷区', 'relation_id': '1759477'}
    replies[('nominatim', '/search')] = '[]'
    with pytest.raises(ValueError):
        run('get_relation_id({"name": "どこにも無い区"})')


def test_count_tag_in_area_makes_the_area_from_the_relation_and_counts(service):
    calls, replies = service
    replies[('overpass', '/api/interpreter')] = '{"elements": [{"tags": {"total": "459"}}]}'
    result = run('count_tag_in_area({"name": "渋谷区", "id_type": "relation_id", "id_value": "1759477"}, "amenity", "cafe")')
    assert result == {'name': '渋谷区', 'relation_id': '1759477', 'tag': 'amenity=cafe', 'count': 459}
    assert '(area:3601759477)' in calls[-1][3] and 'nwr["amenity"="cafe"]' in calls[-1][3]


def test_tag_usage_count_takes_the_total_of_type_all(service):
    _, replies = service
    replies[('taginfo', '/api/4/tag/stats')] = '{"data": [{"type": "all", "count": 8213}, {"type": "nodes", "count": 7041}]}'
    assert run('tag_usage_count("cuisine", "ramen")') == {'key': 'cuisine', 'value': 'ramen', 'count': 8213}


def test_route_summary_posts_json_with_the_costing(service):
    calls, replies = service
    replies[('valhalla', '/route')] = '{"trip": {"summary": {"length": 4.03, "time": 2904.0}}}'
    result = run('route_summary(35.658, 139.7016, 35.6896, 139.7006, costing="pedestrian")')
    assert result == {'costing': 'pedestrian', 'length_km': 4.03, 'time_s': 2904.0, 'time_min': 48.4}
    assert calls[-1][4] == 'application/json' and '"costing": "pedestrian"' in calls[-1][3]
