"""Composition, as in Voyager: a Skill learned for one Intent is called inside the function written for another.

Real local LLM, embedding, Docker, Gateway and services. The first Intent looks up a ward's OSM relation; the
second counts cafes in the ward and is expected to call the first Skill to find the relation instead of writing
the lookup again. Needs GEO_VOYAGER_EMBEDDING_BASE_URL and GEO_VOYAGER_EMBEDDING_MODEL.
"""
from dataclasses import asdict
import json
import os

import pytest

from bench.infra import benchmark_environment
from geo_voyager.critic import Critic
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.llama_client import LlamaClient
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.target_ref import TargetRef
from geo_voyager.worker import Worker

LOOKUP = Intent('Nominatim で東京都の区を名前で検索し、その区の OSM relation ID を求める',
                service_ids=('nominatim',), target=TargetRef('渋谷区'))
COUNT = Intent('区の名前から OSM relation ID を調べ、その区の境界内の amenity=cafe の地物数を Overpass で数える',
               service_ids=('nominatim', 'overpass'), target=TargetRef('渋谷区'))


def test_a_skill_learned_for_one_intent_is_called_by_the_next(tmp_path):
    base, model = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL'), os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base or not model:
        pytest.skip('The embedding service is not configured')
    library = SkillLibrary(tmp_path / 'skills')
    llm = LlamaClient()
    with benchmark_environment() as names:
        executor = IntentExecutor(SkillRetriever(library, EmbeddingClient(base, model)), Worker(names['internal']),
                                  SkillCandidateGenerator(llm), Critic(llm), library, SkillCandidateRepairer(llm))
        first = executor.execute(LOOKUP)
        print('FIRST:', json.dumps(asdict(first), ensure_ascii=False, default=str), flush=True)
        assert first.critique.success and first.learned_skill is not None
        second = executor.execute(COUNT)
        print('SECOND:', json.dumps(asdict(second), ensure_ascii=False, default=str), flush=True)
        for name in library.names():
            for version in library.versions(name):
                print(f'--- {name}@v{version}\n' + library.get(name, version).code, flush=True)
        assert second.critique.success
        assert first.learned_skill in second.called_skills          # the lookup was reused, not rewritten
