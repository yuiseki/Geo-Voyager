import re
from typing import Sequence

from .execution_attempt import ExecutionAttempt
from .execution_failure import ExecutionFailure
from .repair_stats import error_line

EXCERPT_RADIUS = 2
_CANDIDATE_FRAME = re.compile(r'File "<candidate>", line (\d+)')


def failing_line_excerpt(code: str, failure: ExecutionFailure) -> str:
    """The candidate source around the innermost failing frame, with the failing line marked."""
    frames = _CANDIDATE_FRAME.findall(failure.stderr)
    lines = code.splitlines()
    if not frames or not 1 <= int(frames[-1]) <= len(lines):
        return ''
    failing = int(frames[-1])
    first, last = max(1, failing - EXCERPT_RADIUS), min(len(lines), failing + EXCERPT_RADIUS)
    return '\n'.join(f'{">>" if n == failing else "  "} {n}: {lines[n - 1]}' for n in range(first, last + 1))


def attempt_history_text(attempts: Sequence[ExecutionAttempt]) -> str:
    """What each earlier attempt failed with, and whether the code really changed."""
    rows = []
    for index, attempt in enumerate(attempts):
        error = error_line(attempt.failure) if attempt.failure else '成功'
        if index and attempt.code == attempts[index - 1].code:
            note = '（直前の試行とコードが同一）'
        else:
            earlier = next((n for n in range(index - 1) if attempts[n].code == attempt.code), None)
            if earlier is not None:
                note = f'（試行{earlier + 1}とコードが同一）'
            elif index:
                note = '（直前の試行からコードは変わった）'
            else:
                note = ''
        rows.append(f'試行{index + 1}: {error}{note}')
    if len(attempts) >= 2 and all(a.failure for a in attempts[-2:]) \
            and error_line(attempts[-1].failure) == error_line(attempts[-2].failure):
        rows.append('同じエラーが繰り返されている。直前の修正は原因に効いていない。別の原因を疑うこと。')
    return '\n'.join(rows)
