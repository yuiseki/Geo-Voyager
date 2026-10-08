from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_embedding_cache import SkillEmbeddingCache
from geo_voyager.skill_vector_store import SkillVectorStore


def vector(x, y):
    return [x, y] + [0.0] * 382


def test_sync_search_incremental_changes_and_rebuild(tmp_path):
    library = SkillLibrary(tmp_path)
    a, b = Skill(uuid4(), 'a', 'code'), Skill(uuid4(), 'b', 'code')
    for skill in (a, b):
        library.add(skill)
    client = Mock(model='granite-embedding')
    client.embed.side_effect = lambda texts: [dict(a=vector(1, 0), b=vector(0, 1),
                                                 c=vector(-1, 0), changed=vector(0.8, 0.2))[text] for text in texts]
    cache = SkillEmbeddingCache(client, root=tmp_path)
    store = SkillVectorStore(tmp_path / 'vectordb' / 'skills.duckdb')
    store.sync(library, cache)
    assert client.embed.call_count == 2
    assert store.search(vector(1, 0), 2) == [a.id, b.id]
    client.reset_mock()
    store.sync(library, cache)
    client.embed.assert_not_called()
    c = Skill(uuid4(), 'c', 'code')
    library.add(c)
    store.sync(library, cache)
    client.embed.assert_called_once_with(['c'])
    client.reset_mock()
    (tmp_path / str(a.id) / 'description.txt').write_text('changed')
    store.sync(library, cache)
    client.embed.assert_called_once_with(['changed'])
    client.reset_mock()
    # Remove the Skill from the Library without deleting its source files.
    (tmp_path / str(b.id)).rename(tmp_path / 'removed-skill')
    store.sync(library, cache)
    assert store.search(vector(0, 1), 5) == [a.id, c.id]
    client.embed.assert_not_called()
    # A new empty DB is equivalent to losing the derived DB; keep temp files intact.
    rebuilt = SkillVectorStore(tmp_path / 'rebuilt.duckdb')
    rebuilt.sync(library, cache)
    assert rebuilt.search(vector(1, 0), 5) == [a.id, c.id]
    client.embed.assert_not_called()


@pytest.mark.parametrize('k', [0, -1])
def test_invalid_k(tmp_path, k):
    with pytest.raises(ValueError):
        SkillVectorStore(tmp_path / 'index.duckdb').search(vector(1, 0), k)


@pytest.mark.parametrize('query', [[], [1.0], [0.0] * 384, [float('nan')] * 384, [float('inf')] * 384])
def test_invalid_query_is_rejected(tmp_path, query):
    with pytest.raises(ValueError):
        SkillVectorStore(tmp_path / 'index.duckdb').search(query, 1)


def test_model_metadata_change_updates_db_using_cache_without_http(tmp_path):
    library = SkillLibrary(tmp_path)
    skill = Skill(uuid4(), 'a', 'code')
    library.add(skill)
    client = Mock(model='granite-embedding')
    client.embed.return_value = [vector(1, 0)]
    cache = SkillEmbeddingCache(client, root=tmp_path)
    store = SkillVectorStore(tmp_path / 'index.duckdb')
    store.sync(library, cache)
    with store._connect() as connection:
        connection.execute("UPDATE skill_embeddings SET model='outdated'")
    client.reset_mock()
    store.sync(library, cache)
    client.embed.assert_not_called()
    with store._connect() as connection:
        assert connection.execute('SELECT model FROM skill_embeddings').fetchone()[0] == client.model
