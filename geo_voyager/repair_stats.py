from hashlib import sha256

from .execution_failure import ExecutionFailure
from .intent_execution import IntentExecution

STDERR_TAIL_LINES = 3

# Checked in order. The final line of a traceback names the exception.
_FAILURE_PATTERNS = (
    ('syntax', ('SyntaxError', 'IndentationError')),
    ('empty_result', ('No results', 'no results', 'not found', 'Not found', 'Empty', 'empty')),
    ('api', ('HTTP Error', 'HTTPError', 'returned HTTP', 'URLError', 'timed out', 'remark')),
    ('data_shape', ('KeyError', 'IndexError', 'JSONDecodeError', 'string indices must be',
                    'has no attribute', 'not subscriptable', 'unhashable', 'ValueError: could not convert')),
    ('assertion', ('AssertionError',)),
)


def classify_failure(failure: ExecutionFailure) -> str:
    lines = [line for line in failure.stderr.splitlines() if line.strip()]
    last = lines[-1] if lines else ''
    for name, needles in _FAILURE_PATTERNS:
        if any(needle in last for needle in needles):
            return name
    return 'other'


def _stderr_tail(failure: ExecutionFailure) -> str:
    lines = [line for line in failure.stderr.splitlines() if line.strip()]
    return '\n'.join(lines[-STDERR_TAIL_LINES:])


def intent_record(intent_text: str, execution: IntentExecution) -> dict:
    """One JSON-serialisable row. It holds code hashes and stderr tails, not code."""
    attempts = list(execution.attempts)
    reused = execution.selected_skill_id is not None
    candidates = attempts[1:] if reused else attempts
    outcome_at = next((i for i, attempt in enumerate(candidates) if attempt.failure is None), None)
    hashes = [sha256(attempt.code.encode()).hexdigest() for attempt in candidates]
    return {
        'intent': intent_text,
        'reused_skill_failed': reused and attempts[0].failure is not None,
        'reused_skill_succeeded': reused and len(attempts) == 1 and attempts[0].failure is None,
        'candidate_attempts': len(candidates),
        'outcome_at': outcome_at,
        'failure_types': [classify_failure(attempt.failure) for attempt in candidates if attempt.failure],
        'oscillation': any(code in hashes[:i] for i, code in enumerate(hashes)),
        'critic_success': execution.critique.success,
        'critic_reason': execution.critique.reason,
        'attempts': [
            {'code_sha256': code, 'ok': attempt.failure is None,
             'stderr_tail': _stderr_tail(attempt.failure) if attempt.failure else ''}
            for code, attempt in zip(hashes, candidates)
        ],
    }


def success_at(records: list[dict], k: int) -> float | None:
    """Share of candidate chains whose execution succeeded within the first k+1 attempts."""
    chains = [record for record in records if record['candidate_attempts'] > 0]
    if not chains:
        return None
    return sum(1 for r in chains if r['outcome_at'] is not None and r['outcome_at'] <= k) / len(chains)


def summarize(records: list[dict]) -> dict:
    types: dict[str, int] = {}
    for record in records:
        for name in record['failure_types']:
            types[name] = types.get(name, 0) + 1
    return {
        'intents': len(records),
        'success_at': {str(k): success_at(records, k) for k in (0, 1, 2)},
        'failure_types': dict(sorted(types.items())),
        'oscillations': sum(1 for record in records if record['oscillation']),
    }
