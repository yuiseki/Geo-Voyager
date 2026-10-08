from uuid import UUID

import pytest

from geo_voyager.skill import SkillLibrary

ID = UUID('72c549dd-e449-4bef-97f1-e3a2eab27d64')


def test_reads_skill_files_from_uuid_directory(tmp_path):
    directory = tmp_path / str(ID)
    directory.mkdir()
    (directory / 'code.py').write_text('print("ok")\n')
    (directory / 'description.txt').write_text('テストの説明\n')
    library = SkillLibrary(tmp_path)
    skill = library.get(ID)
    assert skill.id == ID
    assert skill.description == 'テストの説明\n'
    assert skill.code == 'print("ok")\n'
    assert library.get(str(ID)) == skill
    assert library.all() == [skill]


@pytest.mark.parametrize('directory_name', ['vectordb', 'not-a-uuid'])
def test_ignores_non_uuid_directories_even_if_files_exist(tmp_path, directory_name):
    directory = tmp_path / directory_name
    directory.mkdir()
    (directory / 'code.py').write_text('print("ok")')
    (directory / 'description.txt').write_text('説明')
    assert SkillLibrary(tmp_path).all() == []
    with pytest.raises(ValueError):
        SkillLibrary(tmp_path).get(directory_name)


@pytest.mark.parametrize('missing', ['code.py', 'description.txt'])
def test_ignores_incomplete_skills(tmp_path, missing):
    directory = tmp_path / str(ID)
    directory.mkdir()
    other = 'description.txt' if missing == 'code.py' else 'code.py'
    (directory / other).write_text('内容')
    library = SkillLibrary(tmp_path)
    assert library.all() == []
    with pytest.raises(KeyError):
        library.get(ID)
