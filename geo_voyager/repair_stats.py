from hashlib import sha256
import re

from .execution_failure import ExecutionFailure
from .intent_execution import IntentExecution

ERROR_LINE_LIMIT = 300
OBSERVATION_HEAD_LIMIT = 500
_EXCEPTION_LINE = re.compile(r'^[\w.]*(?:Error|Exception|Exit|Interrupt)\b')
_HTTP_STATUS = re.compile(r'\bHTTP(?: Error)? (\d{3})\b')

# Checked in order against the exception line, which names the failure.
_FAILURE_PATTERNS = (
    ('syntax', ('SyntaxError', 'IndentationError')),
    ('empty_result', ('No results', 'no results', 'not found', 'Not found', 'Empty', 'empty')),
    ('data_shape', ('KeyError', 'IndexError', 'JSONDecodeError', 'string indices must be',
                    'has no attribute', 'not subscriptable', 'unhashable', 'could not convert')),
    ('assertion', ('AssertionError',)),
)


def error_line(failure: ExecutionFailure) -> str:
    """The last exception line of the traceback. Service error bodies can follow it."""
    lines = [line for line in failure.stderr.splitlines() if line.strip()]
    for line in reversed(lines):
        if _EXCEPTION_LINE.match(line):
            return line[:ERROR_LINE_LIMIT]
    return ''


def classify_failure(failure: ExecutionFailure) -> str:
    line = error_line(failure)
    status = _HTTP_STATUS.search(line)
    if status:
        return 'api_syntax' if status.group(1) in ('400', '404', '405', '414') else 'api_transient'
    if 'TimeoutError' in line or 'timed out' in line or 'URLError' in line:
        return 'api_transient'
    for name, needles in _FAILURE_PATTERNS:
        if any(needle in line for needle in needles):
            return name
    return 'other'


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
        'observation_head': (execution.observations[0].text[:OBSERVATION_HEAD_LIMIT]
                             if execution.observations else ''),
        'critic_success': execution.critique.success,
        'critic_reason': execution.critique.reason,
        'attempts': [
            {'code_sha256': code, 'ok': attempt.failure is None,
             'error_line': error_line(attempt.failure) if attempt.failure else ''}
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


def summarize_goals(rows: list[dict]) -> dict:
    return {
        'goals': len(rows),
        'correct': sum(1 for row in rows if row.get('correct') is True),
        'critic_success': sum(1 for row in rows if row.get('goal_critic_success')),
        'critic_false_positive': sum(1 for row in rows
                                     if row.get('goal_critic_success') and row.get('correct') is False),
        'oracle_missing': sum(1 for row in rows if row.get('correct') is None),
    }
