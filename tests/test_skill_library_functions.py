import pytest

from geo_voyager.skill_library import SkillLibrary, link

COUNT = '''import json
from geo_voyager.control_primitives import call_service


def count_tag_in_area(key, value, relation_id):
    """Count the features with the tag key=value in the area of an OSM relation."""
    area = int(relation_id) + 3600000000
    return area
'''
COMPARE = '''def compare_tags_in_area(relation_id, first, second):
    """Count two tags in one area and say which is more common."""
    counts = {tag: count_tag_in_area(*tag.split("="), relation_id) for tag in (first, second)}
    return max(counts, key=counts.get)
'''
WINNER = '''def winner_of_two_wards(first_id, second_id, tag):
    """Say which of two wards has more features with the tag."""
    a, b = (count_tag_in_area(*tag.split("="), i) for i in (first_id, second_id))
    return first_id if a >= b else second_id
'''


@pytest.fixture
def library(tmp_path):
    return SkillLibrary(tmp_path / 'skills')


def test_a_skill_is_kept_by_name_and_read_back(library):
    assert library.add(COUNT) == 1
    skill = library.get('count_tag_in_area')
    assert skill.name == 'count_tag_in_area' and skill.code == COUNT.strip() and library.names() == ['count_tag_in_area']


def test_saving_a_name_again_keeps_the_old_version(library):
    library.add(COUNT)
    newer = COUNT.replace('return area', 'return area + 0')
    assert library.add(newer) == 2
    assert library.get('count_tag_in_area').code == newer.strip()
    assert library.get('count_tag_in_area', version=1).code == COUNT.strip()
    assert library.versions('count_tag_in_area') == [1, 2]


def test_the_same_code_again_is_not_a_new_version(library):
    library.add(COUNT)
    assert library.add(COUNT + '\n\n') == 1 and library.versions('count_tag_in_area') == [1]


def test_a_skill_that_calls_an_unknown_skill_is_refused(library):
    with pytest.raises(ValueError, match='count_tag_in_area'):
        library.add(COMPARE)            # count_tag_in_area is not in the library yet


def test_a_skill_may_call_primitives_and_saved_skills(library):
    library.add(COUNT)
    assert library.add(COMPARE) == 1


def test_an_unknown_name_is_a_key_error(library):
    with pytest.raises(KeyError):
        library.get('nothing')


def test_link_puts_the_called_skills_and_their_callees_before_the_program_once_each(library):
    library.add(COUNT)
    library.add(COMPARE)
    program = 'print(compare_tags_in_area("1759477", "amenity=cafe", "amenity=restaurant"))'
    linked = link(program, library)
    assert linked.index('def count_tag_in_area') < linked.index('def compare_tags_in_area') < linked.index(program)
    assert linked.count('def count_tag_in_area') == 1


def test_link_leaves_a_program_that_calls_no_skill_unchanged(library):
    library.add(COUNT)
    assert link('print(len([1, 2]))', library) == 'print(len([1, 2]))'


def test_a_program_that_defines_a_function_with_a_skill_name_uses_its_own(library):
    library.add(COUNT)
    program = 'def count_tag_in_area(*a):\n    return 0\nprint(count_tag_in_area())'
    assert link(program, library) == program


def test_skills_shared_by_two_callers_are_loaded_once(library):
    library.add(COUNT)
    library.add(COMPARE)
    library.add(WINNER)
    linked = link('compare_tags_in_area("1", "a=b", "c=d")\nwinner_of_two_wards("1", "2", "a=b")', library)
    assert linked.count('def count_tag_in_area') == 1


def test_the_linked_program_runs(library):
    library.add(COUNT)
    library.add(COMPARE)
    namespace = {}
    exec(link('result = compare_tags_in_area("1", "a=b", "c=d")', library), namespace)
    assert namespace['result'] in ('a=b', 'c=d')


def test_a_cycle_made_by_a_later_version_is_refused_when_linking(library):
    library.add('def a():\n    """A."""\n    return 1')
    library.add('def b():\n    """B."""\n    return a()')
    library.add('def a():\n    """A, now through b."""\n    return b()')
    with pytest.raises(ValueError, match='cycle'):
        link('a()', library)


def test_a_skill_that_calls_itself_is_not_a_cycle(library):
    library.add('def fact(n):\n    """Factorial."""\n    return 1 if n < 2 else n * fact(n - 1)')
    namespace = {}
    exec(link('result = fact(5)', library), namespace)
    assert namespace['result'] == 120
