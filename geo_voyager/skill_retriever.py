"""Find the Skills whose descriptions are closest to an Intent (as Voyager does with its vector DB).

The embedding of each Skill's description is kept next to that version of the Skill, with the model and the
digest of the description, so a new version or another model is embedded again and nothing else is.
"""
import hashlib
import json
import math

from .skill_function import SkillFunction
from .skill_library import SkillLibrary


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.hypot(*a) * math.hypot(*b)
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0


class SkillRetriever:
    def __init__(self, library: SkillLibrary, embedding_client) -> None:
        self.library = library
        self.embedding_client = embedding_client

    def _vectors(self, skills: list[SkillFunction]) -> list[list[float]]:
        vectors, missing = {}, []
        for skill in skills:
            path = self.library.version_dir(skill.name) / 'embedding.json'
            key = {'model': self.embedding_client.model,
                   'description_sha256': hashlib.sha256(skill.description.encode('utf-8')).hexdigest()}
            try:
                cached = json.loads(path.read_text(encoding='utf-8'))
                if all(cached.get(name) == value for name, value in key.items()):
                    vectors[skill.name] = cached['embedding']
                    continue
            except (FileNotFoundError, ValueError, KeyError):
                pass
            missing.append((skill, path, key))
        if missing:
            for (skill, path, key), vector in zip(missing, self.embedding_client.embed([s.description for s, _, _ in missing])):
                path.write_text(json.dumps({**key, 'embedding': vector}), encoding='utf-8')
                vectors[skill.name] = vector
        return [vectors[skill.name] for skill in skills]

    def retrieve(self, text: str, k: int = 4) -> list[SkillFunction]:
        if k < 1:
            raise ValueError('k must be positive')
        skills = self.library.all()
        if not skills:
            return []
        vectors = self._vectors(skills)
        query = self.embedding_client.embed([text])[0]
        ranked = sorted(zip(skills, vectors), key=lambda pair: -_cosine(query, pair[1]))
        return [skill for skill, _ in ranked[:k]]
