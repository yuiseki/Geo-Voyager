"""The events of a Goal as JSON objects, one per line, and back.

The events are those of geo_voyager.goal_history: a step, a Planner failure, a final Critic failure. Written as they
happen and read back the same, they let a stopped Goal go on from its next step, and the records made at the end of
a Goal (the trace, the Exploration Graph, the World Graph) can be made from them.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from .critique import Critique
from .execution_failure import ExecutionFailure
from .goal_history import FinalCriticFailure, HistoryEntry, PlannerFailure
from .intent import Intent
from .observation import Observation
from .target_ref import TargetRef


def _intent_to_dict(intent: Intent) -> dict:
    return {
        'text': intent.text, 'dataset_ids': list(intent.dataset_ids), 'service_ids': list(intent.service_ids),
        'previous_observations': [observation.text for observation in intent.previous_observations],
        'requires_context': intent.requires_context,
        'target': intent.target.to_dict() if intent.target is not None else None,
        'result_name': intent.result_name,
        'inputs': list(intent.inputs) if intent.inputs is not None else None,
        'input_notes': list(intent.input_notes),
    }


def _intent_from_dict(data: dict) -> Intent:
    return Intent(
        data['text'], tuple(data['dataset_ids']), tuple(data['service_ids']),
        tuple(Observation(text) for text in data['previous_observations']), data['requires_context'],
        TargetRef.from_dict(data['target']) if data['target'] is not None else None, data['result_name'],
        tuple(data['inputs']) if data['inputs'] is not None else None, tuple(data['input_notes']))


def event_to_dict(event) -> dict:
    if isinstance(event, HistoryEntry):
        failure = event.failure
        return {
            'kind': 'step', 'step': event.step, 'intent': _intent_to_dict(event.intent),
            'observations': [observation.text for observation in event.observations],
            'critique': {'success': event.critique.success, 'reason': event.critique.reason} if event.critique else None,
            'failure': {'message': failure.message, 'stdout': failure.stdout, 'stderr': failure.stderr,
                        'exit_code': failure.exit_code} if failure is not None else None,
            'called_skills': list(event.called_skills), 'learned_skill': event.learned_skill,
            'targets': [target.to_dict() for target in event.targets], 'attempts': event.attempts,
        }
    if isinstance(event, PlannerFailure):
        return {'kind': 'planner_failure', 'reason': event.reason, 'reply': event.reply, 'after_step': event.after_step}
    if isinstance(event, FinalCriticFailure):
        return {'kind': 'final_critic_failure', 'reason': event.reason, 'after_step': event.after_step}
    raise TypeError(f'not an event of a Goal: {type(event).__name__}')


def event_from_dict(data: dict):
    kind = data.get('kind')
    if kind == 'step':
        critique, failure = data['critique'], data['failure']
        return HistoryEntry(
            data['step'], _intent_from_dict(data['intent']), tuple(Observation(text) for text in data['observations']),
            Critique(critique['success'], critique['reason']) if critique is not None else None,
            ExecutionFailure(failure['message'], failure['stdout'], failure['stderr'], failure['exit_code'])
            if failure is not None else None,
            tuple(data['called_skills']), data['learned_skill'],
            tuple(TargetRef.from_dict(target) for target in data['targets']), data['attempts'])
    if kind == 'planner_failure':
        return PlannerFailure(data['reason'], data['reply'], data['after_step'])
    if kind == 'final_critic_failure':
        return FinalCriticFailure(data['reason'], data['after_step'])
    raise ValueError(f'not an event of a Goal: {kind!r}')


@dataclass(frozen=True)
class LoggedGoal:
    goal: str
    memory: str | None
    events: tuple
    ended: bool
    stop_reason: str | None
    success: bool | None
    # Why the curriculum chose the Goal, for whoever reads the record; no model is shown it again.
    reason: str = ''

    @property
    def history(self) -> tuple[HistoryEntry, ...]:
        """The steps among the events, as AdaptiveGoalExecution.history: the records made at the end of a Goal (the
        trace, the Exploration Graph, the World Graph) read a log as they read the run."""
        return tuple(event for event in self.events if isinstance(event, HistoryEntry))


class EventLog:
    """The log of one Goal: its start (the Goal and the memory it was given), each event as it happens, and its end
    (how it stopped and whether it was answered). The end keeps no Critic's words (ADR 0011). A log without its end
    is a Goal that stopped on the way."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _write(self, row: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a') as file:
            file.write(json.dumps(row, ensure_ascii=False) + '\n')

    def start(self, goal: str, memory: str | None = None, *, reason: str = '') -> None:
        self._write({'kind': 'goal_started', 'goal': goal, 'memory': memory, 'reason': reason})

    def append(self, event) -> None:
        self._write(event_to_dict(event))

    def end(self, stop_reason: str, *, success: bool) -> None:
        self._write({'kind': 'goal_ended', 'stop_reason': stop_reason, 'success': success})

    def read(self) -> LoggedGoal:
        rows = [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
        if not rows or rows[0].get('kind') != 'goal_started':
            raise ValueError(f'{self.path}: a log starts with goal_started')
        end = rows[-1] if rows[-1].get('kind') == 'goal_ended' else None
        events = tuple(event_from_dict(row) for row in rows[1:len(rows) - (end is not None)])
        return LoggedGoal(rows[0]['goal'], rows[0]['memory'], events, end is not None,
                          end['stop_reason'] if end else None, end['success'] if end else None, rows[0]['reason'])
