from dataclasses import dataclass
from uuid import UUID

from .critique import Critique
from .observation import Observation


@dataclass(frozen=True)
class IntentExecution:
    observations: list[Observation]
    retrieved_skill_ids: tuple[UUID, ...]
    selected_skill_id: UUID | None
    learned_skill_id: UUID | None
    critique: Critique
