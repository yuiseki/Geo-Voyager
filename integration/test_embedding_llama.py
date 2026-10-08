"""既存 llama.cpp embedding endpoint の明示的な integration。"""

import math
import os

import pytest

from geo_voyager.embedding_client import EmbeddingClient


@pytest.mark.skipif(
    not os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL') or not os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL'),
    reason='Embedding endpoint and model must be configured explicitly',
)
def test_japanese_batch_embeddings_are_finite_and_have_equal_dimensions():
    client = EmbeddingClient(
        base_url=os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'],
        model=os.environ['GEO_VOYAGER_EMBEDDING_MODEL'],
    )
    vectors = client.embed([
        '東京都23区で人口が最も多い区と人口を求める。',
        '行政区域の人口データから人口が最も少ない区を調べる。',
    ])
    assert len(vectors) == 2
    assert len(vectors[0]) == len(vectors[1]) > 0
    assert all(math.isfinite(value) for vector in vectors for value in vector)
    print(f'endpoint={client.endpoint}, model={client.model}')
    print(f'vectors={len(vectors)}, dimensions={[len(vector) for vector in vectors]}, finite=True')
