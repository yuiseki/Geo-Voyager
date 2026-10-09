"""What a Goal has done so far, as the Planner sees it when it decides the next step.

The history is append-only. An entry is one executed Intent with everything that came out of it: the
Observations, the Critic's verdict, the failure if there was one, the Skill it reused or learned, and
the targets (a name with a stable id) that the step made known for the first time.
"""
from dataclasses import dataclass
from typing import Iterator
from uuid import UUID

from .critique import Critique
from .execution_failure import ExecutionFailure
from .intent import Intent
from .intent_execution import IntentExecution
from .observation import Observation
from .target_identity import discover_targets


def intent_key(intent: Intent) -> tuple:
    """What makes two Intents the same step: the wording, the resources and the target."""
    return (' '.join(intent.text.split()), intent.dataset_ids, intent.service_ids, intent.target_name)


@dataclass(frozen=True)
class HistoryEntry:
    step: int
    intent: Intent
    observations: tuple[Observation, ...]
    critique: Critique | None
    failure: ExecutionFailure | None
    reused_skill_id: UUID | None
    learned_skill_id: UUID | None
    # Targets this step made known for the first time. Empty for a step that did not succeed.
    targets: tuple[dict, ...]

    @property
    def succeeded(self) -> bool:
        return self.failure is None and self.critique is not None and self.critique.success

    @classmethod
    def from_execution(cls, step: int, intent: Intent, execution: IntentExecution, history: 'GoalHistory') -> 'HistoryEntry':
        succeeded = execution.failure is None and execution.critique.success
        known = history.targets()
        new = tuple(target for target in discover_targets(tuple(execution.observations)) if target not in known) if succeeded else ()
        skill_ok = execution.selected_skill_critique is not None and execution.selected_skill_critique.success
        return cls(step, intent, tuple(execution.observations), execution.critique, execution.failure,
                   execution.selected_skill_id if skill_ok else None, execution.learned_skill_id, new)


class GoalHistory:
    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []

    @property
    def entries(self) -> tuple[HistoryEntry, ...]:
        return tuple(self._entries)

    def append(self, entry: HistoryEntry) -> None:
        if entry.step != len(self._entries) + 1:
            raise ValueError(f'Step {entry.step} does not follow step {len(self._entries)}')
        self._entries.append(entry)

    def observations(self) -> tuple[Observation, ...]:
        """The Observations of the steps that succeeded. A failed step's output is not carried forward."""
        return tuple(observation for entry in self._entries if entry.succeeded for observation in entry.observations)

    def targets(self) -> tuple[dict, ...]:
        """The targets known so far, in the order they were first made known. Failed steps add none."""
        known: list[dict] = []
        for entry in self._entries:
            if entry.succeeded:
                known.extend(target for target in entry.targets if target not in known)
        return tuple(known)

    def entries_for(self, intent: Intent) -> list[HistoryEntry]:
        return [entry for entry in self._entries if intent_key(entry.intent) == intent_key(intent)]

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[HistoryEntry]:
        return iter(self._entries)


OBSERVATION_LIMIT = 500
OBSERVATIONS_SHOWN = 3


def _bounded(text: str, limit: int = OBSERVATION_LIMIT) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + f'…（{len(text) - limit} 文字省略）'


def render_history(history: GoalHistory) -> str:
    """The history as text for the Planner: each step with its outcome, then the targets made known."""
    from .repair_stats import error_line
    if not len(history):
        return 'まだ何も実行していない。'
    parts = []
    for entry in history:
        intent = entry.intent
        resources = ', '.join(intent.service_ids + intent.dataset_ids) or 'なし（前段の Observation の集計）'
        status = '成功' if entry.succeeded else ('実行失敗' if entry.failure is not None else 'Critic が不十分と判定')
        lines = [f'step {entry.step}: {intent.text}',
                 f'  リソース: {resources}' + (f' / 対象: {intent.target_name}' if intent.target_name else ''),
                 f'  結果: {status}']
        if entry.failure is not None:
            lines.append('  実行失敗: ' + (error_line(entry.failure) or entry.failure.message))
        if entry.critique is not None:
            lines.append(f'  Critic: {"成功" if entry.critique.success else "失敗"}: {entry.critique.reason}')
        lines += [f'  Observation: {_bounded(observation.text)}' for observation in entry.observations[:OBSERVATIONS_SHOWN]]
        if entry.reused_skill_id is not None:
            lines.append(f'  再利用した Skill: {str(entry.reused_skill_id)[:8]}')
        if entry.learned_skill_id is not None:
            lines.append(f'  学習した Skill: {str(entry.learned_skill_id)[:8]}')
        parts.append('\n'.join(lines))
    targets = history.targets()
    if targets:
        parts.append('判明した対象（前段の Observation で分かった名前と安定ID）:\n' + '\n'.join(
            '- ' + ', '.join(f'{key}: {value}' for key, value in target.items()) for target in targets))
    return '\n'.join(parts)
