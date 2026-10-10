import pytest

from geo_voyager.place_names import place_words_in


@pytest.mark.parametrize('name,target,found', [
    ('count_hotels_in_taito', '台東区', ['taito']),
    ('get_setagaya_relation_id', '世田谷区', ['setagaya']),
    ('count_cafe_in_shibuya', '新宿区', ['shibuya']),            # another ward is a place name too
    ('get_tokyo_tower_coordinates', 'Tokyo Tower', ['tokyo', 'tower']),
])
def test_a_place_in_a_function_name_is_found(name, target, found):
    assert place_words_in(name, target) == found


@pytest.mark.parametrize('name,target', [
    ('count_tag_in_area', '台東区'),
    ('get_ward_relation_id', '渋谷区'),
    ('count_hotels_in_area', None),
    ('compare_two_counts', None),
    ('get_ota_value', None),                                       # 'ota' alone is too common to refuse
])
def test_a_generic_name_is_not(name, target):
    assert place_words_in(name, target) == []
