from dataclasses import dataclass

from .critique import Critique
from .execution_failure import ExecutionFailure
from .execution_attempt import ExecutionAttempt
from .observation import Observation


@dataclass(frozen=True)
class IntentExecution:
    """What one Intent did. Skills are named 'name@vN' (geo_voyager.skill_library)."""
    observations: list[Observation]
    retrieved_skills: tuple[str, ...]     # shown to the Generator
    called_skills: tuple[str, ...]        # saved Skills the final code called (linked in front of it)
    learned_skill: str | None             # the new Skill saved from the final code, when the Critic accepted it
    critique: Critique
    failure: ExecutionFailure | None = None
    attempts: tuple[ExecutionAttempt, ...] = ()
    note: str | None = None               # for example why the accepted code could not be saved as a Skill
