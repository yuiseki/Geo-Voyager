"""The events of a Goal as JSON objects, one per line, and back.

The events are those of geo_voyager.goal_history: a step, a Planner failure, a final Critic failure. Written as they
happen and read back the same, they let a stopped Goal go on from its next step, and the records made at the end of
a Goal (the trace, the Exploration Graph, the World Graph) can be made from them.
"""
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
            'targets': [target.to_dict() for target in event.targets],
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
            tuple(TargetRef.from_dict(target) for target in data['targets']))
    if kind == 'planner_failure':
        return PlannerFailure(data['reason'], data['reply'], data['after_step'])
    if kind == 'final_critic_failure':
        return FinalCriticFailure(data['reason'], data['after_step'])
    raise ValueError(f'not an event of a Goal: {kind!r}')
