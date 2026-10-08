from dataclasses import dataclass
from uuid import UUID

from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
from .observation import Observation


@dataclass(frozen=True)
class IntentExecution:
    observations: list[Observation]
    retrieved_skill_ids: tuple[UUID, ...]
    selected_skill_id: UUID | None
    learned_skill_id: UUID | None
    critique: Critique
    selected_skill_critique: Critique | None
    failure: ExecutionFailure | None = None
    attempts: tuple[ExecutionAttempt, ...] = ()
