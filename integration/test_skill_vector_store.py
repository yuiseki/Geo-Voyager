"""実embedding・persistent vss・cacheだけからの再構築とEXPLAIN。"""
import json
import os
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_embedding_cache import SkillEmbeddingCache
from geo_voyager.skill_vector_store import SEARCH_SQL, SkillVectorStore


def test_real_sync_cache_rebuild_and_hnsw_plan(tmp_path):
    base = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base or not model:
        pytest.skip('Embedding endpoint and model must be explicitly configured')
    library = SkillLibrary(tmp_path / 'skill_library')
    for skill in SkillLibrary().all():
        library.add(skill)
    real_client = EmbeddingClient(base, model)
    client = Mock(wraps=real_client, model=model)
    cache = SkillEmbeddingCache(client, root=library.root)
    store = SkillVectorStore(library.root / 'vectordb' / 'skills.duckdb')
    store.sync(library, cache)
    first = sum(len(call.args[0]) for call in client.embed.call_args_list)
    assert first == 6
    client.reset_mock()
    store.sync(library, cache)
    client.embed.assert_not_called()
    query = real_client.embed(['東京都23区で人口が最も多い区と人口を求める'])[0]
    before = store.search(query, 4)
    # Preserve the former DB rather than deleting temporary files.
    store.path.rename(store.path.with_suffix('.previous.duckdb'))
    store.sync(library, cache)
    client.embed.assert_not_called()
    assert store.search(query, 4) == before
    with store._connect() as connection:
        assert connection.execute('SELECT count(*) FROM skill_embeddings').fetchone()[0] == 6
        plan = connection.execute('EXPLAIN ' + SEARCH_SQL, [query, 4]).fetchone()[1]
    assert 'HNSW_INDEX_SCAN' in plan
    skill = library.all()[0]
    example = json.loads((library.root / str(skill.id) / 'description_embedding.json').read_text())
    report = dict(initial_embedding_texts=first, second_sync_embedding_texts=0,
                  rebuild_embedding_texts=0, cache_example=example, hnsw_plan=plan,
                  result_ids=[str(skill_id) for skill_id in before])
    path = tmp_path / 'vector_store.json'
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('initial sync:', first, 'second sync: 0 rebuild: 0', flush=True)
    print(plan, flush=True)
    print('vector store report:', path, flush=True)
