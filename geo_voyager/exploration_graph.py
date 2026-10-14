"""What exploration tried, one record per Goal it tried, and what the next try of a Goal is given (ADR 0011).

The events are those of geo_voyager.goal_history (a step, a Planner failure, a final Critic failure); this module
has none of its own. From them a deterministic filter keeps the failures checked without a model: an execution
error, a time-out, a contract the code or the Planner broke, an output over the limit, rows that are the same. Those
come out the same whenever the code runs. A Critic's verdict and an unchecked value do not: given to the next try, a
Critic's wrong rejection (港区 and 目黒区 do not touch) became a requirement of an Intent there. A CheckedFailure
has no field for them, and the text for the Planner is made from CheckedFailures only.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

from .execution_failure import ExecutionFailure
from .goal_executor import AdaptiveGoalExecution
from .goal_history import HistoryEntry, PlannerFailure

LINE_LIMIT = 250
MEMORY_LIMIT = 2500
KINDS = {
    'execution_error': '実行のエラー',
    'timeout': '実行の時間切れ',
    'code_contract': 'コードが実行前の契約検査で拒まれた',
    'output_too_long': '出力が上限を超えた',
    'duplicate_rows': '出力に同じ行が重複した',
    'planner_contract': 'Planner の応答が検査で拒まれた',
}
# The line of a traceback or a check that names what went wrong: "KeyError: 'name'", "OutputTooLong: ...".
_NAMED_LINE = re.compile(r'^[A-Za-z_][\w.]*: ')


@dataclass(frozen=True)
class CheckedFailure:
    """A failure found without a model. Nothing here is a judgement, an Observation or what the model wrote."""
    step: int
    intent: str
    resources: tuple[str, ...]
    kind: str
    line: str

    @classmethod
    def from_dict(cls, row: dict) -> 'CheckedFailure':
        """Only the fields of a CheckedFailure are read, whatever else a stored row holds."""
        return cls(int(row['step']), str(row['intent']), tuple(row['resources']), str(row['kind']), str(row['line']))


def _bounded(text: str) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= LINE_LIMIT else text[:LINE_LIMIT] + '…'


def _execution_failure(entry: HistoryEntry) -> CheckedFailure:
    failure: ExecutionFailure = entry.failure
    named = [line.strip() for line in failure.stderr.splitlines() if _NAMED_LINE.match(line.strip())]
    line = named[-1] if named else failure.message
    if 'timed out' in failure.message:
        kind = 'timeout'
    elif line.startswith('OutputTooLong'):
        kind = 'output_too_long'
    elif line.startswith('DuplicateRows'):
        kind = 'duplicate_rows'
    elif 'Candidate breaks' in line:
        kind = 'code_contract'
    else:
        kind = 'execution_error'
    intent = entry.intent
    return CheckedFailure(entry.step, intent.text, intent.dataset_ids + intent.service_ids, kind, _bounded(line))


def checked_failures(events) -> tuple[CheckedFailure, ...]:
    """The failures among a Goal's events that were checked without a model, in order. A step the Critic judged
    (accepted or rejected) and a final Critic failure are left out, with their Observations.

    To keep another kind of mechanical fact (a result of 0 rows, read from the output by code), add its reading here
    as a kind; the record, the text and the tests of what is kept out stay as they are (ADR 0011).
    """
    kept = []
    for event in events:
        if isinstance(event, HistoryEntry) and event.failure is not None:
            kept.append(_execution_failure(event))
        elif isinstance(event, PlannerFailure):
            kept.append(CheckedFailure(event.after_step, '', (), 'planner_contract', _bounded(event.reason)))
    return tuple(kept)


class ExplorationGraph:
    """Every Goal exploration tried, one JSON line each, appended as it goes."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def record(self, number: int, result: AdaptiveGoalExecution | None, *, success: bool, explored_at: str,
               elapsed: float, goal: str | None = None, error: str | None = None, curriculum_reason: str = '',
               memory: bool = False) -> dict:
        """Add the try of a Goal. result is None when the Goal broke (error says how)."""
        row = {
            'number': number, 'goal': result.goal if result is not None else goal, 'curriculum_reason': curriculum_reason,
            'success': success, 'stop_reason': result.stop_reason if result is not None else 'error',
            # Read by the curriculum only, not by the next try of the Goal (ADR 0011, the path left).
            'reason': result.critique.reason if result is not None else error,
            'steps': len(result.history) if result is not None else None,
            'elapsed': elapsed, 'explored_at': explored_at, 'memory': memory,
            'checked_failures': [asdict(failure) for failure in checked_failures(result.events)] if result is not None else [],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a') as file:
            file.write(json.dumps(row, ensure_ascii=False) + '\n')
        return row

    def attempts(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    @staticmethod
    def render(failures: tuple[CheckedFailure, ...]) -> str:
        """The failures as text for the Planner, the latest kept when they do not fit."""
        lines = []
        for failure in failures:
            where = f'step {failure.step}「{failure.intent[:200]}」' if failure.intent else f'step {failure.step} のあと'
            used = f'（{", ".join(failure.resources)}）' if failure.resources else ''
            lines.append(f'- {where}{used}: {KINDS[failure.kind]}: {failure.line}')
        kept, size = [], 0
        for line in reversed(lines):
            if size + len(line) + 1 > MEMORY_LIMIT - 20:
                kept.append('- （これより前は略）')
                break
            kept.append(line)
            size += len(line) + 1
        return '\n'.join(reversed(kept))

    def memory(self, goal: str) -> str | None:
        """What the next try of the Goal is given: the checked failures of its latest try, if that try did not answer
        it and had any. None otherwise."""
        tries = [attempt for attempt in self.attempts() if attempt['goal'] == goal]
        if not tries or tries[-1]['success']:
            return None
        failures = tuple(CheckedFailure.from_dict(row) for row in tries[-1].get('checked_failures', []))
        return self.render(failures) if failures else None

    def memories(self) -> dict[str, str]:
        """{Goal: memory} for every Goal tried that has one."""
        goals = dict.fromkeys(attempt['goal'] for attempt in self.attempts())
        return {goal: memory for goal in goals if (memory := self.memory(goal)) is not None}

