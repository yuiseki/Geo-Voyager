from dataclasses import dataclass
from pathlib import Path
from uuid import UUID


@dataclass(frozen=True)
class Skill:
    id: UUID
    description: str
    code: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", UUID(str(self.id)))


class SkillLibrary:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1] / "skill_library"

    def _read(self, directory: Path, skill_id: UUID) -> Skill:
        code = directory / "code.py"
        description = directory / "description.txt"
        if not code.is_file() or not description.is_file():
            raise KeyError(skill_id)
        return Skill(id=skill_id, description=description.read_text(encoding="utf-8"), code=code.read_text(encoding="utf-8"))

    def get(self, skill_id: UUID | str) -> Skill:
        skill_id = UUID(str(skill_id))
        return self._read(self.root / str(skill_id), skill_id)

    def all(self) -> list[Skill]:
        skills = []
        for directory in sorted(self.root.iterdir()):
            if not directory.is_dir():
                continue
            try:
                skill_id = UUID(directory.name)
            except ValueError:
                continue
            try:
                skills.append(self._read(directory, skill_id))
            except KeyError:
                continue
        return skills
