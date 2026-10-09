import json

from geo_voyager.observation import Observation
from geo_voyager.target_identity import resolve_target


def obs(value) -> Observation:
    return Observation(json.dumps(value, ensure_ascii=False))


def test_a_target_is_found_by_name_in_a_list_of_targets():
    wards = obs([{'name': '世田谷区', 'relation_id': '1'}, {'name': '港区', 'relation_id': '2'}])
    assert resolve_target('港区', (wards,)) == {'name': '港区', 'relation_id': '2'}


def test_a_target_is_found_in_a_single_object_observation():
    assert resolve_target('渋谷区', (obs({'name': '渋谷区', 'relation_id': '3'}),)) == {'name': '渋谷区', 'relation_id': '3'}


def test_position_does_not_matter():
    wards = [{'name': str(n), 'relation_id': str(n)} for n in range(5)]
    assert resolve_target('3', (obs(wards),)) == {'name': '3', 'relation_id': '3'}
    assert resolve_target('3', (obs(list(reversed(wards))),)) == {'name': '3', 'relation_id': '3'}


def test_the_same_target_seen_twice_is_one_target():
    first = obs({'name': '渋谷区', 'relation_id': '3'})
    second = obs({'name': '渋谷区', 'relation_id': '3', 'count': 459})
    assert resolve_target('渋谷区', (first, second)) == {'name': '渋谷区', 'relation_id': '3'}


def test_two_different_ids_for_one_name_are_ambiguous():
    items = obs([{'name': '府中', 'relation_id': '1'}, {'name': '府中', 'relation_id': '2'}])
    assert resolve_target('府中', (items,)) is None


def test_missing_target_or_unparseable_observations_resolve_to_none():
    assert resolve_target('港区', (obs([{'name': '渋谷区', 'relation_id': '3'}]),)) is None
    assert resolve_target('港区', (Observation('not json'),)) is None
    assert resolve_target('港区', ()) is None


def test_names_are_matched_exactly_not_by_substring():
    assert resolve_target('区', (obs([{'name': '港区', 'relation_id': '2'}]),)) is None


def test_targets_are_discovered_in_an_object_a_list_and_a_list_under_a_key():
    from geo_voyager.target_identity import discover_targets
    found = discover_targets((
        obs({'name': '渋谷区', 'relation_id': '1'}),
        obs([{'name': '港区', 'relation_id': '2'}, {'name': '新宿区', 'id': 3}]),
        obs({'results': [{'name': '台東区', 'relation_id': '4'}]}),
    ))
    assert found == [{'name': '渋谷区', 'relation_id': '1'}, {'name': '港区', 'relation_id': '2'},
                     {'name': '新宿区', 'id': 3}, {'name': '台東区', 'relation_id': '4'}]


def test_an_object_without_a_name_or_a_stable_id_is_not_a_target():
    from geo_voyager.target_identity import discover_targets
    assert discover_targets((obs({'name': '渋谷区'}), obs({'relation_id': '1'}), obs({'count': 3}),
                             obs({'name': 'cuisine', 'relation_id': None}))) == []


def test_a_target_seen_again_with_more_fields_is_one_target_and_only_name_and_id_are_kept():
    from geo_voyager.target_identity import discover_targets
    found = discover_targets((obs({'name': '渋谷区', 'relation_id': '1'}), obs({'name': '渋谷区', 'relation_id': '1', 'count': 459})))
    assert found == [{'name': '渋谷区', 'relation_id': '1'}]


def test_discovery_ignores_text_and_malformed_json():
    from geo_voyager.target_identity import discover_targets
    assert discover_targets((Observation('not json'), Observation('[1, 2]'), Observation('"x"'))) == []
