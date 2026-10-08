from unittest.mock import Mock, call
from uuid import uuid4

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever


def test_retrieval_syncs_then_embeds_only_query_and_preserves_search_order(tmp_path):
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
    intent = Intent('調査', ('admin',))
    assert retriever.retrieve(intent, k=4) == [b, a]
    assert store.mock_calls == [call.sync(library, cache), call.search(query, 4)]
    client.embed.assert_called_once_with([intent.text])


def test_empty_library_returns_empty_without_embedding(tmp_path):
    client, store = Mock(model='granite-embedding'), Mock()
    store.search.return_value = []
    assert SkillRetriever(SkillLibrary(tmp_path), client, store=store).retrieve(Intent('調査', ('admin',))) == []
    client.embed.assert_not_called()


@pytest.mark.parametrize('k', [0, -1])
def test_nonpositive_k_fails_before_sync(tmp_path, k):
    client, store = Mock(model='granite-embedding'), Mock()
    with pytest.raises(ValueError):
        SkillRetriever(SkillLibrary(tmp_path), client, store=store).retrieve(Intent('調査', ('admin',)), k)
    store.sync.assert_not_called()
    client.embed.assert_not_called()
