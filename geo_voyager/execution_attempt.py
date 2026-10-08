from dataclasses import dataclass

from .execution_failure import ExecutionFailure
from .observation import Observation


@dataclass(frozen=True)
class ExecutionAttempt:
    code: str
    observations: list[Observation]
    failure: ExecutionFailure | None
