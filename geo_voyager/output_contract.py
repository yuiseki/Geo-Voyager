"""What an output must not be, found without a model, before the Critic reads it.

A rule here is one a model was asked to judge and judged both ways. The output fails as the code's failure, so the
repair reads what is wrong; the Critic is left the question only a model can answer, whether the output answers the
Intent.
"""
import collections
import json


def _rows(value) -> list | None:
    if isinstance(value, dict):
        value = next((item for item in value.values() if isinstance(item, list)), None)
    if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
        return value
    return None


def output_problem(text: str) -> str | None:
    """Why the output can not be an answer, or None.

    Rows that are the same: a row of ekidata is a station on a line, so a station came back once per line (東京 16
    times in the 23 rows of memory_run2 goal 1). The Critic passed 2 of the 8 such lists it was shown.
    """
    try:
        rows = _rows(json.loads(text))
    except ValueError:
        return None
    if rows is None:
        return None
    counts = collections.Counter(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)
    repeated = [(row, count) for row, count in counts.items() if count > 1]
    if not repeated:
        return None
    extra = sum(count - 1 for _, count in repeated)
    row, count = max(repeated, key=lambda item: item[1])
    return (f'DuplicateRows: {len(rows)} 行のうち {extra} 行が、ほかの行と同じ（重複）。例: {row} が {count} 回。'
            '表の 1 行が何か（grain）を確かめ、答えの 1 件が 1 行になるように重複を除く')
