from unittest.mock import Mock

import pytest

from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever


def skill(name, description):
    return f'def {name}():\n    """{description}"""\n    return 1\n'


class FakeEmbedding:
    """A text's vector: one axis per keyword it contains."""
    model = 'fake'
    WORDS = ('cafe', 'station', 'population', 'route')

    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        return [[1.0 if word in text else 0.0 for word in self.WORDS] + [0.1] for text in texts]


@pytest.fixture
def library(tmp_path):
    library = SkillLibrary(tmp_path / 'skills')
    library.add(skill('count_cafes', 'Count cafe features in an area.'))
    library.add(skill('northernmost_station', 'Find the station with the largest latitude.'))
    library.add(skill('total_population', 'Sum the population of areas.'))
    return library


def test_the_closest_descriptions_come_first(library):
    retriever = SkillRetriever(library, FakeEmbedding())
    assert [s.name for s in retriever.retrieve('How many cafe are there?', 2)][0] == 'count_cafes'
    assert retriever.retrieve('population of the wards', 1)[0].name == 'total_population'


def test_k_is_capped_by_the_library_and_an_empty_library_gives_nothing(library, tmp_path):
    assert len(SkillRetriever(library, FakeEmbedding()).retrieve('cafe', 10)) == 3
    assert SkillRetriever(SkillLibrary(tmp_path / 'empty'), FakeEmbedding()).retrieve('cafe', 3) == []


def test_embeddings_are_cached_per_version_and_a_new_version_is_embedded_again(library):
    embedding = FakeEmbedding()
    SkillRetriever(library, embedding).retrieve('cafe', 1)
    first = embedding.calls
    SkillRetriever(library, embedding).retrieve('cafe', 1)
    assert embedding.calls == first + 1                 # only the query
    library.add(skill('count_cafes', 'Count cafe and station features.'))
    SkillRetriever(library, embedding).retrieve('cafe', 1)
    assert embedding.calls == first + 3                 # the new version, and the query


def test_a_cache_from_another_model_is_not_used(library):
    SkillRetriever(library, FakeEmbedding()).retrieve('cafe', 1)
    other = FakeEmbedding(); other.model = 'other'
    SkillRetriever(library, other).retrieve('cafe', 1)
    assert other.calls == 2                              # all three descriptions in one call, and the query


def test_k_must_be_positive(library):
    with pytest.raises(ValueError):
        SkillRetriever(library, FakeEmbedding()).retrieve('cafe', 0)
