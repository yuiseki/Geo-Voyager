from dataclasses import dataclass

from .critique import Critique
from .execution_failure import ExecutionFailure
from .observation import Observation


@dataclass(frozen=True)
class ExecutionAttempt:
    code: str
    observations: list[Observation]
    failure: ExecutionFailure | None
    # 'runtime' for the first candidate and its repairs after an execution failure,
    # 'semantic' for the one repair after the Critic rejected a run that had succeeded.
    route: str = 'runtime'
    # The Critic's verdict on this attempt's observations, when the Critic was asked.
    critique: Critique | None = None
    # For a semantic attempt: the Critic reason it was asked to fix.
    trigger: str | None = None
    # False when a semantic repair was proposed but not run (unchanged, repeated, hardcoded, invalid).
    executed: bool = True
    note: str = ''
