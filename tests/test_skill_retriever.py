from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever


def setup_retriever(tmp_path, vectors):
    library = SkillLibrary(tmp_path)
    skills = [Skill(uuid4(), description, 'print(1)') for description in ('最大人口', '最小人口')]
    for skill in skills:
        library.add(skill)
    skills = library.all()
    client = Mock()
    client.embed.side_effect = [vectors, [[1.0, 0.0]]]
    return SkillRetriever(library, client), client, skills


def test_retrieve_embeds_descriptions_and_intent_and_ranks_by_cosine(tmp_path):
    retriever, client, skills = setup_retriever(tmp_path, [[1.0, 1.0], [0.5, 0.0]])
    intent = Intent('人口最大の区を求める', ('yuiseki/jp-admin-2026-09',))
    assert retriever.retrieve(intent, k=1) == [skills[1]]
    assert client.embed.call_args_list[0].args == ([skill.description for skill in skills],)
    assert client.embed.call_args_list[1].args == ([intent.text],)


def test_k_larger_than_library_returns_all_in_rank_order(tmp_path):
    retriever, _, skills = setup_retriever(tmp_path, [[-1.0, 0.0], [1.0, 0.0]])
    assert retriever.retrieve(Intent('人口', ('admin',)), k=3) == [skills[1], skills[0]]


def test_empty_library_returns_empty_without_embedding(tmp_path):
    client = Mock()
    assert SkillRetriever(SkillLibrary(tmp_path), client).retrieve(Intent('人口', ('admin',))) == []
    client.embed.assert_not_called()


@pytest.mark.parametrize('k', [0, -1])
def test_reject_nonpositive_k(tmp_path, k):
    retriever, client, _ = setup_retriever(tmp_path, [[1.0, 0.0]] * 2)
    with pytest.raises(ValueError):
        retriever.retrieve(Intent('人口', ('admin',)), k=k)
    client.embed.assert_not_called()


@pytest.mark.parametrize('vectors', [[[0.0, 0.0], [1.0, 0.0]], [[1.0], [1.0]]])
def test_reject_zero_norm_and_cross_call_dimension_mismatch(tmp_path, vectors):
    retriever, _, _ = setup_retriever(tmp_path, vectors)
    with pytest.raises(ValueError):
        retriever.retrieve(Intent('人口', ('admin',)))
