"""Failure categories for benchmark rows, derived afterwards from the recorded signals.

Rules, in order, for a Goal whose answer was wrong:
 1. an exception ended the run, by what raised it:
      the Planner or IntentExecutor rejected the plan, or it names an
      unregistered resource (ValueError, KeyError)                          -> planning
      the Generator or Repairer broke its output format (ValueError)        -> codegen
      the Critic broke its output format (ValueError)                       -> critic-format
      sandbox timeout, Docker, network                                      -> execution
    or no Intent declares a resource the Goal needs                         -> planning
 2. at the first bad step:
      all candidate attempts failed, only with transient service errors     -> execution
      all candidate attempts failed otherwise                               -> codegen
      it ran but returned another target than the Goal's ward               -> retrieval-selection
      it ran but the Critic rejected it, last step is local aggregation     -> aggregation
      it ran but the Critic rejected it otherwise                           -> semantic-completion
 3. no bad step, yet the answer is wrong (the Critic let it through)
      last step is local aggregation                                        -> aggregation
      otherwise                                                             -> semantic-completion
A row without an oracle answer is 'unmeasured'. These are heuristics on recorded signals and
should be spot-checked against the prompts and responses kept in each run directory.
"""
from collections import Counter
import re

from geo_voyager.repair_stats import OBSERVATION_HEAD_LIMIT

CATEGORIES = ('planning', 'retrieval-selection', 'codegen', 'execution', 'semantic-completion', 'aggregation',
              'critic-format')
AREA_OFFSET = 3600000000
_RELATION_ID = re.compile(r'relation_id"?\s*:\s*"?(\d+)')


def _error_category(error: str) -> str:
    """An exception that escaped the whole Goal run, by what raised it."""
    kind, _, message = error.partition(': ')
    if kind == 'KeyError':
        return 'planning'  # the plan names a service or dataset that is not registered
    if kind == 'ValueError':
        if message.startswith('Candidate'):
            return 'codegen'  # the Generator or Repairer did not follow its output format
        if message.startswith('Critique'):
            return 'critic-format'
        return 'planning'  # the Planner or IntentExecutor rejected the plan
    return 'execution'  # sandbox timeout, Docker, network


def _resources(step: dict) -> set[str]:
    return set(step.get('services', [])) | set(step.get('datasets', []))


def _exhausted(step: dict) -> bool:
    return step['candidate_attempts'] > 0 and step['outcome_at'] is None


def _returns_another_target(step: dict, target: int | None) -> bool:
    if len(step.get('observation_head', '')) >= OBSERVATION_HEAD_LIMIT:
        return False  # cut off: the target may be in the part that was not recorded
    ids = [int(found) for found in _RELATION_ID.findall(step.get('observation_head', ''))]
    return bool(target) and bool(ids) and target not in ids and target + AREA_OFFSET not in ids


def _local_aggregation(step: dict) -> bool:
    return bool(step.get('requires_context')) and not _resources(step)


def classify(row: dict) -> dict | None:
    if row.get('correct') is True:
        return None
    if row.get('correct') is None:
        return {'category': 'unmeasured', 'first_wrong_step': None, 'evidence': 'no oracle answer'}
    if row.get('error'):
        return {'category': _error_category(row['error']), 'first_wrong_step': None,
                'evidence': row['error'][:200]}
    steps = row['intents']
    used = set().union(*(_resources(step) for step in steps)) if steps else set()
    missing = sorted(set(row.get('required', [])) - used)
    if missing:
        return {'category': 'planning', 'first_wrong_step': 1,
                'evidence': f'no Intent declares {missing}'}
    for number, step in enumerate(steps, start=1):
        if _exhausted(step):
            transient = bool(step['failure_types']) and all(t == 'api_transient' for t in step['failure_types'])
            return {'category': 'execution' if transient else 'codegen', 'first_wrong_step': number,
                    'evidence': f'failures {step["failure_types"]}'}
        if _returns_another_target(step, row.get('target_relation')):
            return {'category': 'retrieval-selection', 'first_wrong_step': number,
                    'evidence': step['observation_head'][:120]}
        if step.get('critic_success') is False:
            last = number == len(steps)
            return {'category': 'aggregation' if last and _local_aggregation(step) else 'semantic-completion',
                    'first_wrong_step': number, 'evidence': 'critic rejected a step that ran'}
    last_local = bool(steps) and _local_aggregation(steps[-1])
    return {'category': 'aggregation' if last_local else 'semantic-completion',
            'first_wrong_step': len(steps) or None, 'evidence': 'every step ran and passed, the answer is wrong'}


def plan_signature(row: dict) -> tuple:
    return tuple(tuple(sorted(_resources(step))) for step in row['intents'])


def planner_variance(rows: list[dict]) -> dict:
    planned = [row for row in rows if not row.get('error')]
    signatures = Counter(plan_signature(row) for row in planned)
    return {
        'runs': len(rows),
        'plan_errors': len(rows) - len(planned),
        'distinct_plans': len(signatures),
        'step_counts': dict(sorted(Counter(len(row['intents']) for row in planned).items())),
        'modal_share': (max(signatures.values()) / len(planned)) if planned else None,
    }
