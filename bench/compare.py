"""Compare two benchmark runs: python -m bench.compare OLD.jsonl NEW.jsonl

Rows are re-judged with the current judges first, so both sides are scored the same way.
The Fisher test is there to keep a difference between two runs of about a hundred Goals honest.
"""
from math import comb
import json
import sys

from bench.report import build_report, load, rejudge


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test on the table [[a, b], [c, d]]."""
    row1, row2, col1, total = a + b, c + d, a + c, a + b + c + d

    def probability(x: int) -> float:
        return comb(col1, x) * comb(total - col1, row1 - x) / comb(total, row1)

    observed = probability(a)
    low, high = max(0, row1 - (total - col1)), min(row1, col1)
    return min(1.0, sum(p for p in (probability(x) for x in range(low, high + 1)) if p <= observed * (1 + 1e-9)))


def _side(rows: list[dict]) -> dict:
    report = build_report(rows)
    measured = report['measured']
    early = report['first_wrong_step'].get(1, 0) + report['first_wrong_step'].get(2, 0)
    planner = report['planner'].values()
    shares = [item['modal_share'] for item in planner if item['modal_share'] is not None]
    return {
        'runs': report['runs'], 'measured': measured, 'correct': report['correct'],
        'correct_rate': report['correct'] / measured if measured else None,
        'step12_failure_rate': early / measured if measured else None,
        'categories': report['categories'],
        'by_family': {name: f"{entry['correct']}/{entry['runs']}" for name, entry in report['by_family'].items()},
        'critic': report['critic'], 'success_at': report['success_at'],
        'planner': {'mean_distinct_plans': sum(item['distinct_plans'] for item in report['planner'].values())
                    / max(1, len(report['planner'])),
                    'mean_modal_share': sum(shares) / len(shares) if shares else None,
                    'plan_errors': sum(item['plan_errors'] for item in report['planner'].values())},
        '_by_goal': {goal: f"{entry['correct']}/{entry['runs']}" for goal, entry in report['by_goal'].items()},
    }


def compare(old_rows: list[dict], new_rows: list[dict]) -> dict:
    old, new = _side(old_rows), _side(new_rows)
    by_goal = {goal: {'old': old['_by_goal'].get(goal), 'new': new['_by_goal'].get(goal)}
               for goal in sorted(set(old['_by_goal']) | set(new['_by_goal']))}
    for side in (old, new):
        del side['_by_goal']
    return {
        'old': old, 'new': new, 'by_goal': by_goal,
        'planner': {'old': old['planner'], 'new': new['planner']},
        'difference': {
            'correct_rate': new['correct_rate'] - old['correct_rate'],
            'step12_failure_rate': new['step12_failure_rate'] - old['step12_failure_rate'],
            'fisher_p': fisher_exact(new['correct'], new['measured'] - new['correct'],
                                     old['correct'], old['measured'] - old['correct']),
        },
    }


def main() -> None:
    old, new = (rejudge(load([path])) for path in sys.argv[1:3])
    print(json.dumps(compare(old, new), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
