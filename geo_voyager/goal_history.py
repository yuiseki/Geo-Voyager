"""What a Goal has done so far, as the Planner sees it when it decides the next step.

The history is append-only. An entry is one executed Intent with everything that came out of it: the
Observations, the Critic's verdict, the failure if there was one, the Skill it reused or learned, and
the targets (a name with a stable id) that the step made known for the first time.
"""
from dataclasses import dataclass
from typing import Iterator

from .critique import Critique
from .execution_failure import ExecutionFailure
from .intent import Intent
from .intent_execution import IntentExecution
from .observation import Observation
from .target_identity import discover_targets
from .target_ref import TargetRef


def intent_key(intent: Intent) -> tuple:
    """What makes two Intents the same step: the wording, the resources and the target."""
    target = intent.target
    target_key = None if target is None else (target.key or ('name', target.name))
    return (' '.join(intent.text.split()), intent.dataset_ids, intent.service_ids, target_key)


@dataclass(frozen=True)
class PlannerFailure:
    """The Planner's reply could not be used: it broke the output format or a contract.

    It is kept so that the next call to the Planner can read what went wrong and plan again.
    """
    reason: str
    # What the model wrote, so the Planner can see the mistake it made.
    reply: str = ''
    # How many steps had been executed when it happened.
    after_step: int = 0


@dataclass(frozen=True)
class FinalCriticFailure:
    """The Planner said DONE, but the Critic found the Goal not answered by what the steps produced."""
    reason: str
    after_step: int = 0


@dataclass(frozen=True)
class HistoryEntry:
    step: int
    intent: Intent
    observations: tuple[Observation, ...]
    critique: Critique | None
    failure: ExecutionFailure | None
    called_skills: tuple[str, ...]      # saved Skills the step's code called ('name@vN')
    learned_skill: str | None           # the Skill saved from the step ('name@vN')
    # Targets this step made known for the first time, each with its stable id. Empty for a step that did not succeed.
    targets: tuple[TargetRef, ...]

    @property
    def succeeded(self) -> bool:
        return self.failure is None and self.critique is not None and self.critique.success

    @classmethod
    def from_execution(cls, step: int, intent: Intent, execution: IntentExecution, history: 'GoalHistory') -> 'HistoryEntry':
        succeeded = execution.failure is None and execution.critique.success
        known = {target.key for target in history.targets()}
        new = tuple(target for target in discover_targets(tuple(execution.observations)) if target.key not in known) if succeeded else ()
        return cls(step, intent, tuple(execution.observations), execution.critique, execution.failure,
                   tuple(execution.called_skills), execution.learned_skill, new)


class GoalHistory:
    """Append-only. Executed steps and the two kinds of failure, in the order they happened.

    len() and iteration are about the executed steps only: a failure is not a step.
    """

    def __init__(self) -> None:
        self._events: list = []

    @property
    def events(self) -> tuple:
        return tuple(self._events)

    @property
    def entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(event for event in self._events if isinstance(event, HistoryEntry))

    def append(self, event) -> None:
        if isinstance(event, HistoryEntry):
            if event.step != len(self) + 1:
                raise ValueError(f'Step {event.step} does not follow step {len(self)}')
        elif not isinstance(event, (PlannerFailure, FinalCriticFailure)):
            raise TypeError(f'Not a history event: {event!r}')
        self._events.append(event)

    def planner_failures(self) -> tuple[PlannerFailure, ...]:
        return tuple(event for event in self._events if isinstance(event, PlannerFailure))

    def final_critic_failures(self) -> tuple[FinalCriticFailure, ...]:
        return tuple(event for event in self._events if isinstance(event, FinalCriticFailure))

    def observations(self) -> tuple[Observation, ...]:
        """The Observations of the steps that succeeded. A failed step's output is not carried forward."""
        return tuple(observation for entry in self.entries if entry.succeeded for observation in entry.observations)

    def targets(self) -> tuple[TargetRef, ...]:
        """The targets known so far, in the order they were first made known. Failed steps add none.

        A target is its stable id: the same id under another name is not a new target.
        """
        known: dict[tuple, TargetRef] = {}
        for entry in self.entries:
            if entry.succeeded:
                for target in entry.targets:
                    known.setdefault(target.key, target)
        return tuple(known.values())

    def entries_for(self, intent: Intent) -> list[HistoryEntry]:
        return [entry for entry in self.entries if intent_key(entry.intent) == intent_key(intent)]

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[HistoryEntry]:
        return iter(self.entries)


OBSERVATION_LIMIT = 500
OBSERVATIONS_SHOWN = 3


def _bounded(text: str, limit: int = OBSERVATION_LIMIT) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + f'…（{len(text) - limit} 文字省略）'


def render_history(history: GoalHistory) -> str:
    """The history as text for the Planner, in the order it happened, then the targets made known."""
    from .repair_stats import error_line
    if not history.events:
        return 'まだ何も実行していない。'
    parts = [] if len(history) else ['まだ何も実行していない。']
    for event in history.events:
        if isinstance(event, PlannerFailure):
            lines = [f'計画の失敗: {event.reason}']
            if event.reply:
                lines.append('  あなたの応答: ' + _bounded(event.reply))
            parts.append('\n'.join(lines))
            continue
        if isinstance(event, FinalCriticFailure):
            parts.append(f'Goal の最終判定が未達: DONE を返したが、Critic は次の理由で Goal の答えが揃っていないと判定した。\n  理由: {event.reason}')
            continue
        entry = event
        intent = entry.intent
        resources = ', '.join(intent.service_ids + intent.dataset_ids) or 'なし（前段の Observation の集計）'
        status = '成功' if entry.succeeded else ('実行失敗' if entry.failure is not None else 'Critic が不十分と判定')
        lines = [f'step {entry.step}: {intent.text}',
                 f'  リソース: {resources}' + (f' / 対象: {intent.target.display()}' if intent.target else ''),
                 f'  結果: {status}']
        if entry.failure is not None:
            lines.append('  実行失敗: ' + (error_line(entry.failure) or entry.failure.message))
        if entry.critique is not None:
            lines.append(f'  Critic: {"成功" if entry.critique.success else "失敗"}: {entry.critique.reason}')
        lines += [f'  Observation: {_bounded(observation.text)}' for observation in entry.observations[:OBSERVATIONS_SHOWN]]
        if entry.called_skills:
            lines.append(f'  呼んだ Skill: {", ".join(entry.called_skills)}')
        if entry.learned_skill is not None:
            lines.append(f'  学習した Skill: {entry.learned_skill}')
        parts.append('\n'.join(lines))
    targets = history.targets()
    if targets:
        parts.append('判明した対象（前段の Observation で分かった名前と安定ID。対象は ID で区別する）:\n' + '\n'.join(
            f'- {target.display()}' for target in targets))
    return '\n'.join(parts)
