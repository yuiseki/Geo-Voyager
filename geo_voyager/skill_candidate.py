from dataclasses import dataclass
from uuid import uuid4

from .skill import Skill


@dataclass(frozen=True)
class SkillCandidate:
    code: str
    description: str


def promote(candidate: SkillCandidate) -> Skill:
    return Skill(id=uuid4(), code=candidate.code, description=candidate.description)
