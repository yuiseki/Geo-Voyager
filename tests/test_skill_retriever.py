from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever


def test_startup_sync_once_then_queries_only_and_preserves_order(tmp_path):
    library = SkillLibrary(tmp_path)
    a, b = Skill(uuid4(), 'a', 'code'), Skill(uuid4(), 'b', 'code')
    library.add(a)
    library.add(b)
    client = Mock(model='granite-embedding')
    query = [1.0] * 384
    client.embed.return_value = [query]
    store, cache = Mock(), Mock()
    store.search.return_value = [b.id, a.id]
    retriever = SkillRetriever(library, client, store=store, cache=cache)
    store.sync.assert_called_once_with(library, cache)
    store.reset_mock()
    library.all = Mock(side_effect=AssertionError('no enumeration during retrieval'))
    intent = Intent('調査', ('admin',))
    assert retriever.retrieve(intent, k=4) == [b, a]
    assert retriever.retrieve(intent, k=4) == [b, a]
    assert store.mock_calls == [call.search(query, 4), call.search(query, 4)]
    assert client.embed.call_args_list == [call([intent.text]), call([intent.text])]
    cache.get.assert_not_called()


def test_empty_index_returns_empty_after_query_embedding(tmp_path):
    client, store = Mock(model='granite-embedding'), Mock()
    store.search.return_value = []
    client.embed.return_value = [[1.0] * 384]
    assert SkillRetriever(SkillLibrary(tmp_path), client, store=store).retrieve(Intent('調査', ('admin',))) == []
    client.embed.assert_called_once_with(['調査'])


@pytest.mark.parametrize('k', [0, -1])
def test_nonpositive_k_fails_without_query_or_extra_sync(tmp_path, k):
    client, store = Mock(model='granite-embedding'), Mock()
    retriever = SkillRetriever(SkillLibrary(tmp_path), client, store=store)
    store.reset_mock()
    with pytest.raises(ValueError):
        retriever.retrieve(Intent('調査', ('admin',)), k)
    store.sync.assert_not_called()
    client.embed.assert_not_called()


def test_learning_upsert_gets_one_cache_without_full_sync(tmp_path):
    library = SkillLibrary(tmp_path)
    client = Mock(model='granite-embedding')
    store, cache = Mock(), Mock(model='granite-embedding')
    retriever = SkillRetriever(library, client, store=store, cache=cache)
    store.reset_mock()
    skill = Skill(uuid4(), 'new skill', 'code')
    library.add(skill)
    embedding = [1.0] * 384
    cache.get.return_value = embedding
    retriever.upsert(skill)
    cache.get.assert_called_once_with(skill)
    store.upsert.assert_called_once_with(skill, embedding, cache.model)
    store.sync.assert_not_called()
    client.embed.assert_not_called()


def test_empty_library_startup_and_search_with_real_index(tmp_path):
    client = Mock(model='granite-embedding')
    client.embed.return_value = [[1.0] * 384]
    retriever = SkillRetriever(SkillLibrary(tmp_path), client)
    client.embed.assert_not_called()
    assert retriever.retrieve(Intent('調査', ('admin',))) == []
    client.embed.assert_called_once_with(['調査'])
