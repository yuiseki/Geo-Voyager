from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    code: str


class SkillLibrary:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def add(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        return self._skills[name]

    def all(self) -> list[Skill]:
        return list(self._skills.values())
