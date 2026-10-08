import os

import pytest

from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever


def test_retrieve_existing_population_skills(tmp_path):
    base_url = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base_url or not model:
        pytest.skip('Embedding endpoint and model must be explicitly configured')
    library = SkillLibrary(tmp_path / 'skill_library')
    for skill in SkillLibrary().all():
        library.add(skill)
    retriever = SkillRetriever(library, EmbeddingClient(base_url, model))
    registered_ids = {skill.id for skill in SkillLibrary().all()}
    for adjective in ('多い', '少ない'):
        intent = Intent(f'東京都23区で人口が最も{adjective}区と人口を求める', ('yuiseki/jp-admin-2026-09',))
        result = retriever.retrieve(intent, k=len(registered_ids))
        print(f'{intent.text} -> {[str(skill.id) for skill in result]}')
        assert len(result) == len(registered_ids)
        assert {skill.id for skill in result} == registered_ids
