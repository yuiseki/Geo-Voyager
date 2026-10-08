import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from .embedding_client import EmbeddingClient
from .skill import Skill, SkillLibrary


DIMENSIONS = 384


def description_sha256(description: str) -> str:
    return hashlib.sha256(description.encode('utf-8')).hexdigest()


def valid_embedding(vector: object) -> bool:
    return (isinstance(vector, list) and len(vector) == DIMENSIONS
            and all(type(value) in (int, float) and math.isfinite(value) for value in vector)
            and math.hypot(*vector) > 0)


class SkillEmbeddingCache:
    def __init__(self, embedding_client: EmbeddingClient, *, root: Path | None = None) -> None:
        if embedding_client.model != 'granite-embedding':
            raise ValueError('Only granite-embedding is supported')
        self.embedding_client = embedding_client
        self.model = embedding_client.model
        self.root = SkillLibrary(root).root

    def get(self, skill: Skill) -> list[float]:
        path = self.root / str(skill.id) / 'description_embedding.json'
        metadata = dict(format_version=1, model=self.model, dimensions=DIMENSIONS,
                        description_sha256=description_sha256(skill.description))
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if (isinstance(data, dict) and all(data.get(key) == value for key, value in metadata.items())
                    and valid_embedding(data.get('embedding'))):
                return data['embedding']
        except (FileNotFoundError, ValueError, UnicodeError):
            pass
        vector = self.embedding_client.embed([skill.description])[0]
        if not valid_embedding(vector):
            raise ValueError('Embedding must have 384 finite values and nonzero norm')
        # Same-directory replacement keeps readers from observing a partial JSON file.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.description_embedding-', suffix='.json', delete=False) as temp:
            json.dump({**metadata, 'embedding': vector}, temp, allow_nan=False)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp.name, path)
        return vector
