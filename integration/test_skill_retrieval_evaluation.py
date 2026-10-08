"""6 Intent の実embedding / LLM評価。正解率を報告し、閾値で隠さない。"""

import json
import math
import os

import pytest

from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from integration.test_initial_analysis_skills import CASES


class RecordedEmbeddings:
    """評価時だけ、Retrieverが実際に使ったベクトルを記録する。"""

    def __init__(self, client):
        self.client = client
        self.vectors = {}

    def embed(self, texts):
        vectors = self.client.embed(texts)
        self.vectors.update(zip(texts, vectors))
        return vectors


def test_six_intents_retriever_top_four_and_selector(tmp_path):
    base_url = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base_url or not model:
        pytest.skip('Embedding endpoint and model must be explicitly configured')
    library = SkillLibrary()
    assert len(library.all()) == 6
    embeddings = RecordedEmbeddings(EmbeddingClient(base_url, model))
    retriever = SkillRetriever(library, embeddings)
    selector = SkillSelector()
    cases = (
        ('東京都23区で人口が最も多い区と人口を求める', 'yuiseki/jp-admin-2026-09', '72c549dd-e449-4bef-97f1-e3a2eab27d64'),
        ('東京都23区で人口が最も少ない区と人口を求める', 'yuiseki/jp-admin-2026-09', 'e722f367-1ff1-4796-89a3-48cfd1dfcb68'),
        *CASES,
    )
    results = []
    for text, dataset_id, correct_id in cases:
        intent = Intent(text, (dataset_id,))
        candidates = retriever.retrieve(intent, k=4)
        assert len(candidates) == 4
        query = embeddings.vectors[intent.text]
        query_norm = math.hypot(*query)
        top_four = []
        for rank, skill in enumerate(candidates, start=1):
            vector = embeddings.vectors[skill.description]
            norm = math.hypot(*vector)
            similarity = sum((a / norm) * (b / query_norm) for a, b in zip(vector, query))
            top_four.append({'rank': rank, 'uuid': str(skill.id), 'similarity': similarity})
        scores = [item['similarity'] for item in top_four]
        assert scores == sorted(scores, reverse=True)
        selected = selector.select(intent, candidates)
        assert selected is None or selected in candidates
        selected_id = str(selected.id) if selected else None
        result = {'intent': text, 'correct_uuid': correct_id, 'top_four': top_four,
                  'correct_in_top_four': any(str(skill.id) == correct_id for skill in candidates),
                  'selected_uuid': selected_id, 'correct_selection': selected_id == correct_id}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    assert len(results) == 6
    print('retriever recall@4:', sum(item['correct_in_top_four'] for item in results), '/ 6', flush=True)
    print('selector accuracy:', sum(item['correct_selection'] for item in results), '/ 6', flush=True)
    report = tmp_path / 'skill_evaluation.json'
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('evaluation report:', report, flush=True)
