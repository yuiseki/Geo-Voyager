from .embedding_client import EmbeddingClient
from .intent import Intent
from .skill import Skill, SkillLibrary
from .skill_embedding_cache import SkillEmbeddingCache
from .skill_vector_store import SkillVectorStore


class SkillRetriever:
    def __init__(self, library: SkillLibrary, embedding_client: EmbeddingClient, *,
                 store: SkillVectorStore | None = None, cache: SkillEmbeddingCache | None = None) -> None:
        self.library = library
        self.embedding_client = embedding_client
        self.store = store if store is not None else SkillVectorStore(library.root / 'vectordb' / 'skills.duckdb')
        self.cache = cache if cache is not None else SkillEmbeddingCache(embedding_client, root=library.root)
        self.store.sync(self.library, self.cache)

    def retrieve(self, intent: Intent, k: int = 1) -> list[Skill]:
        if k < 1:
            raise ValueError('k must be positive')
        query = self.embedding_client.embed([intent.text])[0]
        return [self.library.get(skill_id) for skill_id in self.store.search(query, k)]

    def upsert(self, skill: Skill) -> None:
        embedding = self.cache.get(skill)
        self.store.upsert(skill, embedding, self.cache.model)
