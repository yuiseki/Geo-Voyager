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


def test_there_are_six_seed_skills_and_each_says_what_it_does():
    names = LIBRARY.names()
    assert names == ['count_station_records', 'least_populous_area', 'most_populous_area', 'northernmost_station',
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
