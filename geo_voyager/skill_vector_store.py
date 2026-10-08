from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import duckdb

from .skill import Skill, SkillLibrary
from .skill_embedding_cache import SkillEmbeddingCache, description_sha256, valid_embedding


TABLE_SQL = '''CREATE TABLE IF NOT EXISTS skill_embeddings (
                skill_id UUID PRIMARY KEY, description_sha256 VARCHAR NOT NULL,
                model VARCHAR NOT NULL, embedding FLOAT[384] NOT NULL)'''


SEARCH_SQL = '''SELECT skill_id FROM skill_embeddings
ORDER BY array_cosine_distance(embedding, ?::FLOAT[384]) LIMIT ?'''


class SkillVectorStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path is not None else SkillLibrary().root / 'vectordb' / 'skills.duckdb'

    @contextmanager
    def _connect(self):
        if duckdb.__version__ != '1.5.6':
            raise RuntimeError('DuckDB 1.5.6 is required')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Load vss before attaching a persistent DB, including WAL recovery.
        with duckdb.connect(config={'autoinstall_known_extensions': False,
                                    'autoload_known_extensions': False, 'threads': 1}) as connection:
            connection.execute('LOAD vss')
            connection.execute('SET hnsw_enable_experimental_persistence=true')
            quoted_path = str(self.path).replace("'", "''")
            connection.execute(f"ATTACH '{quoted_path}' AS skill_index")
            connection.execute('USE skill_index')
            yield connection

    def sync(self, library: SkillLibrary, cache: SkillEmbeddingCache) -> None:
        skills = library.all()
        with self._connect() as connection:
            connection.execute(TABLE_SQL)
            existing = {row[0]: row[1:] for row in connection.execute(
                'SELECT skill_id, description_sha256, model FROM skill_embeddings').fetchall()}
            live = {skill.id for skill in skills}
            updates = []
            for skill in skills:
                digest = description_sha256(skill.description)
                if existing.get(skill.id) != (digest, cache.model):
                    updates.append((skill.id, digest, cache.model, cache.get(skill)))
            connection.execute('BEGIN')
            try:
                if existing.keys() - live or any(row[0] in existing for row in updates):
                    connection.execute('DROP INDEX IF EXISTS skill_embedding_hnsw')
                for skill_id in existing.keys() - live:
                    connection.execute('DELETE FROM skill_embeddings WHERE skill_id=?', [skill_id])
                for skill_id, digest, model, embedding in updates:
                    if skill_id in existing:
                        connection.execute('''UPDATE skill_embeddings SET description_sha256=?,
                            model=?, embedding=? WHERE skill_id=?''', [digest, model, embedding, skill_id])
                    else:
                        connection.execute('INSERT INTO skill_embeddings VALUES (?, ?, ?, ?)',
                                           [skill_id, digest, model, embedding])
                connection.execute('''CREATE INDEX IF NOT EXISTS skill_embedding_hnsw
                    ON skill_embeddings USING HNSW (embedding) WITH (metric='cosine')''')
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise

    def upsert(self, skill: Skill, embedding: list[float], model: str = 'granite-embedding') -> None:
        if model != 'granite-embedding' or not valid_embedding(embedding):
            raise ValueError('Expected granite-embedding with 384 finite values and nonzero norm')
        with self._connect() as connection:
            connection.execute(TABLE_SQL)
            digest = description_sha256(skill.description)
            exists = connection.execute('SELECT 1 FROM skill_embeddings WHERE skill_id=?', [skill.id]).fetchone()
            connection.execute('BEGIN')
            try:
                if exists:
                    # Persistent vss can retain old row IDs after UPDATE; rebuild only on replacement.
                    connection.execute('DROP INDEX IF EXISTS skill_embedding_hnsw')
                    connection.execute("""UPDATE skill_embeddings SET description_sha256=?,
                        model=?, embedding=? WHERE skill_id=?""", [digest, model, embedding, skill.id])
                else:
                    connection.execute('INSERT INTO skill_embeddings VALUES (?, ?, ?, ?)',
                                       [skill.id, digest, model, embedding])
                connection.execute("""CREATE INDEX IF NOT EXISTS skill_embedding_hnsw
                    ON skill_embeddings USING HNSW (embedding) WITH (metric='cosine')""")
                connection.execute('COMMIT')
            except Exception:
                connection.execute('ROLLBACK')
                raise

    def search(self, query_embedding: list[float], k: int) -> list[UUID]:
        if k < 1:
            raise ValueError('k must be positive')
        if not valid_embedding(query_embedding):
            raise ValueError('Query must have 384 finite values and nonzero norm')
        with self._connect() as connection:
            return [row[0] for row in connection.execute(SEARCH_SQL, [query_embedding, k]).fetchall()]
