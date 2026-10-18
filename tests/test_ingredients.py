"""The ingredients drawn at random for a Goal of exploration: kinds of things OSM maps, areas, measures and an
indicator of the WDI. In exploration 11 (2026-10-15 to 17), 67 of the 72 Goals asked for a largest or smallest, and
most of them of the census's municipalities. Asked for the most expensive tennis court of Tokyo, the curriculum would
have to think of tennis courts and of land prices together; drawn ingredients put such pairs in front of it.
"""
import random

from geo_voyager.ingredients import AREAS, COUNTS, KINDS, MEASURES, Ingredients, draw


def test_the_kinds_are_those_the_frozen_osm_of_the_23_wards_has_one_tag_a_line():
    assert len(KINDS) == 546
    assert 'leisure=pitch' in KINDS and 'sport=tennis' in KINDS and 'amenity=vending_machine' in KINDS
    assert KINDS['amenity=place_of_worship'].startswith('A place where religious services')


def test_the_areas_are_the_23_wards_and_the_measures_include_the_land_prices():
    assert len([area for area in AREAS if area.endswith('区') and area != '東京23区']) == 23
    assert 'ksj-l01-land-price' in MEASURES['公示地価'] and 'WorldPop' in MEASURES['周りの推計人口']


def test_a_draw_depends_only_on_its_seed():
    assert draw(random.Random(7)) == draw(random.Random(7))
    assert draw(random.Random(7)) != draw(random.Random(8))


def test_a_draw_names_three_kinds_two_areas_two_measures_and_an_indicator():
    drawn = draw(random.Random(1))
    assert (len(drawn.kinds), len(drawn.areas), len(drawn.measures), len(drawn.indicators)) == (3, 2, 2, 1)
    assert set(drawn.names()) == {*drawn.kinds, *drawn.areas, *drawn.measures, *drawn.indicators}
    text = drawn.text()
    for kind in drawn.kinds:
        assert kind in text and KINDS[kind][:20] in text


def test_a_kind_says_how_many_the_23_wards_have_for_half_have_fewer_than_fifty():
    # Explore 22: asked of shop=food in 新宿区 and 大田区, and of leisure=amusement_arcade areas in 台東区, the Goals
    # found none and ran out of time. 273 of the 546 kinds have fewer than 50 in all the 23 wards.
    assert COUNTS['shop=food'] == 36 and COUNTS['amenity=parking'] == 23797
    text = Ingredients(('shop=food',), ('新宿区',), ('件数',), ('AG.LND.AGRI.K2',)).text()
    assert 'shop=food（23 区で 36 件。A shop selling food.）' in text
