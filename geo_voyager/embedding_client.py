import json
import math
from urllib.request import Request, urlopen


class EmbeddingClient:
    def __init__(self, base_url: str, model: str) -> None:
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url += '/v1'
        self.endpoint = base_url + '/embeddings'
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            raise ValueError('texts must not be empty')
        request = Request(
            self.endpoint,
            data=json.dumps({
                'model': self.model, 'input': texts, 'encoding_format': 'float',
            }).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST',
        )
        with urlopen(request, timeout=120) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
            raise ValueError('Embedding response must contain a data list')
        data = payload['data']
        if len(data) != len(texts):
            raise ValueError('Embedding count must match input count')
        if any(not isinstance(item, dict) or type(item.get('index')) is not int for item in data):
            raise ValueError('Each embedding must contain an integer index')
        if sorted(item['index'] for item in data) != list(range(len(texts))):
            raise ValueError('Embedding indexes must cover input positions exactly once')
        vectors = []
        for item in sorted(data, key=lambda item: item['index']):
            embedding = item.get('embedding')
            if not isinstance(embedding, list) or not embedding:
                raise ValueError('Embedding must be a non-empty list')
            if any(type(value) not in (int, float) for value in embedding):
                raise ValueError('Embedding values must be numbers')
            vector = [float(value) for value in embedding]
            if not all(math.isfinite(value) for value in vector):
                raise ValueError('Embedding values must be finite')
            vectors.append(vector)
        if any(len(vector) != len(vectors[0]) for vector in vectors):
            raise ValueError('Embedding dimensions must match')
        return vectors
