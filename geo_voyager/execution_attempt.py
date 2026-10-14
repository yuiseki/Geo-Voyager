from dataclasses import dataclass

from .critique import Critique
from .execution_failure import ExecutionFailure
from .observation import Observation


@dataclass(frozen=True)
class ExecutionAttempt:
    code: str
    observations: list[Observation]
    failure: ExecutionFailure | None
    # The Critic's verdict on this attempt's observations, when the Critic was asked.
    critique: Critique | None = None
