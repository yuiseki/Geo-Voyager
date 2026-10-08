import math

from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.skill import Skill, SkillLibrary


class SkillRetriever:
    def __init__(self, library: SkillLibrary, embedding_client: EmbeddingClient) -> None:
        self.library = library
        self.embedding_client = embedding_client

    def retrieve(self, intent: Intent, k: int = 1) -> list[Skill]:
        if k < 1:
            raise ValueError('k must be positive')
        skills = self.library.all()
        if not skills:
            return []
        vectors = self.embedding_client.embed([skill.description for skill in skills])
        query = self.embedding_client.embed([intent.text])[0]
        query_norm = math.hypot(*query)
        if query_norm == 0:
            raise ValueError('Embedding norm must be nonzero')
        scores = []
        for vector in vectors:
            if len(vector) != len(query):
                raise ValueError('Embedding dimensions must match')
            norm = math.hypot(*vector)
            if norm == 0:
                raise ValueError('Embedding norm must be nonzero')
            scores.append(sum((a / norm) * (b / query_norm) for a, b in zip(vector, query)))
        ranked = sorted(zip(skills, scores), key=lambda item: item[1], reverse=True)
        return [skill for skill, _ in ranked[:k]]
