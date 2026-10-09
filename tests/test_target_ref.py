import json

import pytest

from geo_voyager.observation import Observation
from geo_voyager.target_identity import (
    AmbiguousTarget, discover_targets, identity_conflict, resolve_reference, resolve_target)
from geo_voyager.target_ref import TargetRef

MINATO = TargetRef('港区, 東京都, 日本', 'relation_id', '1761717')


def obs(value) -> Observation:
    return Observation(json.dumps(value, ensure_ascii=False))


# ---- the value object

def test_a_target_ref_has_a_name_and_a_stable_id_and_the_id_is_text():
    ref = TargetRef('港区', 'relation_id', 1761717)
    assert (ref.name, ref.id_type, ref.id_value) == ('港区', 'relation_id', '1761717') and ref.resolved
    assert ref.key == ('relation_id', '1761717')


def test_a_name_alone_is_an_unresolved_target_to_look_up():
    ref = TargetRef('港区')
    assert not ref.resolved and ref.key is None and ref.id_type is None and ref.id_value is None


def test_a_target_ref_needs_a_name_and_both_halves_of_the_id_or_neither():
    for args in [('', ), (' ', ), ('港区', 'relation_id'), ('港区', None, '1'), ('港区', 'relation_id', '')]:
        with pytest.raises(ValueError):
            TargetRef(*args)


def test_two_refs_are_the_same_target_by_id_not_by_display_name():
    short, long = TargetRef('港区', 'relation_id', '1761717'), TargetRef('港区, 東京都, 日本', 'relation_id', 1761717)
    assert short.same_target(long) and long.same_target(short)
    assert not short.same_target(TargetRef('港区', 'relation_id', '3554304'))              # same name, another id
    assert not short.same_target(TargetRef('港区', 'osm_id', '1761717'))                   # the id type is part of it


def test_unresolved_refs_can_only_be_compared_by_name():
    assert TargetRef('港区').same_target(TargetRef('港区')) and not TargetRef('港区').same_target(TargetRef('渋谷区'))
    assert not TargetRef('港区').same_target(MINATO)             # a name does not stand for an id


def test_a_ref_round_trips_through_a_dict_and_shows_its_id():
    assert TargetRef.from_dict(MINATO.to_dict()) == MINATO
    assert TargetRef.from_dict({'name': '港区'}) == TargetRef('港区') and TargetRef('港区').to_dict() == {'name': '港区'}
    assert '1761717' in MINATO.display() and 'relation_id' in MINATO.display()


# ---- discovery keeps the id

def test_discovery_returns_refs_with_their_stable_id():
    found = discover_targets((obs({'name': '渋谷区', 'relation_id': 1}), obs([{'name': '新宿区', 'id': '3'}])))
    assert found == [TargetRef('渋谷区', 'relation_id', '1'), TargetRef('新宿区', 'id', '3')]


def test_the_same_id_under_two_display_names_is_one_target_and_the_first_name_is_kept():
    found = discover_targets((obs({'name': '港区, 東京都, 日本', 'relation_id': '1761717'}), obs({'name': '港区', 'relation_id': 1761717, 'count': 22})))
    assert found == [MINATO]


def test_the_same_name_with_two_ids_is_two_targets():
    found = discover_targets((obs([{'name': '港区', 'relation_id': '1761717'}, {'name': '港区', 'relation_id': '99'}]),))
    assert [t.key for t in found] == [('relation_id', '1761717'), ('relation_id', '99')]


# ---- resolving a target in earlier observations: the id decides

def test_a_resolved_target_is_found_by_id_whatever_the_observation_calls_it():
    for name in ('港区', '港区, 東京都, 日本', 'Minato'):
        found = resolve_target(MINATO, (obs([{'name': name, 'relation_id': '1761717'}]),))
        assert found is not None and found.key == ('relation_id', '1761717') and found.name == name


def test_a_resolved_target_is_not_found_by_name_alone():
    assert resolve_target(MINATO, (obs([{'name': '港区, 東京都, 日本', 'relation_id': '999'}]),)) is None


def test_an_unresolved_target_is_found_by_name_when_exactly_one_id_has_it():
    assert resolve_target(TargetRef('渋谷区'), (obs([{'name': '渋谷区', 'relation_id': '1'}]),)) == TargetRef('渋谷区', 'relation_id', '1')
    assert resolve_target(TargetRef('渋谷区'), (obs([{'name': '港区', 'relation_id': '2'}]),)) is None


def test_an_unresolved_target_whose_name_has_two_ids_is_ambiguous_and_not_resolved():
    twin = obs([{'name': '港区', 'relation_id': '1761717'}, {'name': '港区', 'relation_id': '99'}])
    assert resolve_target(TargetRef('港区'), (twin,)) is None


# ---- the guard: a name match never stands in for the id

def test_an_observation_about_the_target_id_has_no_conflict_whatever_its_name():
    assert identity_conflict(MINATO, (obs({'name': '港区', 'relation_id': '1761717', 'count': 22}),)) is None


def test_the_same_name_with_another_id_is_a_conflict():
    reason = identity_conflict(MINATO, (obs({'name': '港区, 東京都, 日本', 'relation_id': '99', 'count': 5}),))
    assert reason and '1761717' in reason and '99' in reason


def test_a_list_that_includes_the_target_among_others_is_not_a_conflict():
    listing = obs([{'name': '渋谷区', 'relation_id': '1'}, {'name': '港区', 'relation_id': '1761717'}])
    assert identity_conflict(MINATO, (listing,)) is None


def test_an_observation_with_no_id_of_that_type_is_left_to_the_judge():
    assert identity_conflict(MINATO, (obs({'answer': 22}), Observation('22件'))) is None


def test_an_unresolved_target_has_no_id_to_conflict_with():
    assert identity_conflict(TargetRef('港区'), (obs({'name': '港区', 'relation_id': '99'}),)) is None


# ---- a reference written by a Planner is matched to a known target

KNOWN = (MINATO, TargetRef('渋谷区', 'relation_id', '1759477'))


def test_a_reference_by_the_exact_name_is_the_known_target():
    assert resolve_reference('渋谷区', KNOWN) == KNOWN[1]
    assert resolve_reference('港区, 東京都, 日本', KNOWN) == MINATO


def test_a_short_name_matches_the_known_display_name_when_only_one_target_has_it():
    assert resolve_reference('港区', KNOWN) == MINATO


def test_a_reference_by_id_is_the_known_target():
    for text in ('relation_id=1761717', 'relation_id: 1761717', '1761717', '港区 (relation_id=1761717)'):
        assert resolve_reference(text, KNOWN) == MINATO, text


def test_a_name_known_under_two_ids_is_refused_and_the_message_lists_the_ids():
    known = KNOWN + (TargetRef('港区, 名古屋市, 愛知県, 日本', 'relation_id', '3554304'),)
    with pytest.raises(AmbiguousTarget) as raised:
        resolve_reference('港区', known)
    assert isinstance(raised.value, ValueError)
    assert '1761717' in str(raised.value) and '3554304' in str(raised.value) and 'ID' in str(raised.value)
    assert resolve_reference('relation_id=3554304', known).id_value == '3554304'        # the id settles it


def test_an_exact_name_still_wins_over_a_display_name_match():
    known = (TargetRef('港区', 'relation_id', '1'), TargetRef('港区, 大阪市, 大阪府, 日本', 'relation_id', '2'))
    assert resolve_reference('港区', known).id_value == '1'


def test_an_unknown_name_is_an_unresolved_target_to_look_up():
    assert resolve_reference('新宿区', KNOWN) == TargetRef('新宿区')
    assert resolve_reference('新宿区', ()) == TargetRef('新宿区')


def test_a_number_is_not_taken_for_an_id_unless_it_is_the_whole_reference_or_marked():
    known = (TargetRef('第3区', 'relation_id', '3'),)
    assert resolve_reference('第3区', known) == known[0]                     # by name
    assert resolve_reference('3丁目', known) == TargetRef('3丁目')           # the 3 inside a name is not an id
