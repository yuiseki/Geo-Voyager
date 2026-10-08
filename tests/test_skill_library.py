import pytest

from geo_voyager.skill import Skill, SkillLibrary


def test_skill_library_add_get_and_all():
    library = SkillLibrary()
    assert library.all() == []
    skill = Skill(name='test', description='テスト', code='print("ok")')
    library.add(skill)
    assert library.get('test') is skill
    assert library.all() == [skill]
    with pytest.raises(KeyError):
        library.get('unknown')
