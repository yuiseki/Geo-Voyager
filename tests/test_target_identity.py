import json

from geo_voyager.observation import Observation
from geo_voyager.target_identity import discover_targets, resolve_target
from geo_voyager.target_ref import TargetRef


def obs(value) -> Observation:
    return Observation(json.dumps(value, ensure_ascii=False))


# The id-first behaviour is in test_target_ref.py. These cover where targets are looked for and how a name alone is used.

def test_targets_are_discovered_in_an_object_a_list_and_a_list_under_a_key():
    found = discover_targets((
        obs({'name': '渋谷区', 'relation_id': '1'}),
        obs([{'name': '港区', 'relation_id': '2'}, {'name': '新宿区', 'id': 3}]),
        obs({'results': [{'name': '台東区', 'relation_id': '4'}]}),
    ))
    assert found == [TargetRef('渋谷区', 'relation_id', '1'), TargetRef('港区', 'relation_id', '2'),
                     TargetRef('新宿区', 'id', '3'), TargetRef('台東区', 'relation_id', '4')]


def test_an_object_without_a_name_or_a_stable_id_is_not_a_target():
    assert discover_targets((obs({'name': '渋谷区'}), obs({'relation_id': '1'}), obs({'count': 3}),
                             obs({'name': 'cuisine', 'relation_id': None}))) == []


def test_discovery_ignores_text_and_malformed_json():
    assert discover_targets((Observation('not json'), Observation('[1, 2]'), Observation('"x"'))) == []


def test_a_name_only_target_is_found_in_a_list_a_single_object_and_at_any_position():
    wards = [{'name': str(n), 'relation_id': str(n)} for n in range(5)]
    for listing in (wards, list(reversed(wards))):
        assert resolve_target(TargetRef('3'), (obs(listing),)) == TargetRef('3', 'relation_id', '3')
    assert resolve_target(TargetRef('渋谷区'), (obs({'name': '渋谷区', 'relation_id': '3'}),)) == TargetRef('渋谷区', 'relation_id', '3')


def test_a_name_only_target_seen_twice_with_the_same_id_is_one_target():
    first = obs({'name': '渋谷区', 'relation_id': '3'})
    second = obs({'name': '渋谷区', 'relation_id': '3', 'count': 459})
    assert resolve_target(TargetRef('渋谷区'), (first, second)) == TargetRef('渋谷区', 'relation_id', '3')


def test_a_name_with_two_ids_is_ambiguous_and_a_missing_name_is_not_found():
    twins = obs([{'name': '府中', 'relation_id': '1'}, {'name': '府中', 'relation_id': '2'}])
    assert resolve_target(TargetRef('府中'), (twins,)) is None
    assert resolve_target(TargetRef('港区'), (obs([{'name': '渋谷区', 'relation_id': '3'}]),)) is None
    assert resolve_target(TargetRef('港区'), (Observation('not json'),)) is None and resolve_target(TargetRef('港区'), ()) is None


def test_names_are_matched_exactly_not_by_substring():
    assert resolve_target(TargetRef('区'), (obs([{'name': '港区', 'relation_id': '2'}]),)) is None
