"""Summarise benchmark runs: python -m bench.report <results.jsonl> [...]"""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

from bench.goals import GOALS
from bench.taxonomy import classify, planner_variance
from geo_voyager.repair_stats import summarize


def load(paths: list[str]) -> list[dict]:
    return [json.loads(line) for path in paths
            for line in Path(path).expanduser().read_text().splitlines() if line.strip()]


def rejudge(rows: list[dict]) -> list[dict]:
    """Recompute correctness from the recorded final Observation with the current judges.

    A judge can be wrong. The recorded answer and the oracle output are enough to judge again,
    so a fixed judge does not need a new run. The recorded verdict is kept as correct_recorded.
    """
    judges = {goal.id: goal.judge for goal in GOALS}
    result = []
    for row in rows:
        if row.get('oracle') is not None and row['id'] in judges:
            final = row.get('final_observation', '')
            row = dict(row, correct=bool(final) and judges[row['id']](final, row['oracle']),
                       correct_recorded=row.get('correct'))
        result.append(row)
    return result


NTH_TEMPLATE = re.compile(r'一覧の\s*[0-9０-９]+\s*番目')


def uses_nth_template(row: dict) -> bool:
    """The Planner prompt tells it to measure a listed target by its position, 一覧のN番目."""
    return any(NTH_TEMPLATE.search(step['intent']) for step in row['intents'])


def family(row: dict) -> str:
    required = row.get('required') or []
    if not required:
        return 'other'
    if '/' in required[0]:
        return 'dataset'
    return {'yuisekin-geosparql': 'geosparql'}.get(required[0], required[0])


def build_report(rows: list[dict]) -> dict:
    classified = [(row, classify(row)) for row in rows]
    failures = [(row, c) for row, c in classified if c and c['category'] != 'unmeasured']
    by_family: dict[str, dict] = defaultdict(lambda: {'runs': 0, 'correct': 0, 'categories': Counter()})
    for row, c in classified:
        entry = by_family[family(row)]
        entry['runs'] += 1
        entry['correct'] += row.get('correct') is True
        if c and c['category'] != 'unmeasured':
            entry['categories'][c['category']] += 1
    by_goal = defaultdict(list)
    for row in rows:
        by_goal[row['id']].append(row)
    measured = [row for row in rows if row.get('correct') is not None]
    intents = [intent for row in rows for intent in row['intents']]
    return {
        'runs': len(rows),
        'measured': len(measured),
        'correct': sum(1 for row in rows if row.get('correct') is True),
        'unmeasured': len(rows) - len(measured),
        'categories': dict(sorted(Counter(c['category'] for _, c in failures).items())),
        'first_wrong_step': dict(sorted(Counter(c['first_wrong_step'] for _, c in failures
                                                if c['first_wrong_step'] is not None).items())),
        'by_family': {name: {**entry, 'categories': dict(sorted(entry['categories'].items()))}
                      for name, entry in sorted(by_family.items())},
        'by_goal': {goal: {'runs': len(items), 'correct': sum(1 for r in items if r.get('correct') is True)}
                    for goal, items in sorted(by_goal.items())},
        'planner': {goal: planner_variance(items) for goal, items in sorted(by_goal.items())},
        'nth_template': {
            key: {'runs': len(group), 'correct': sum(1 for r in group if r.get('correct') is True)}
            for key, group in (('with', [r for r in measured if uses_nth_template(r)]),
                               ('without', [r for r in measured if not uses_nth_template(r)]))},
        'critic': {
            'false_positive': sum(1 for r in rows if r.get('goal_critic_success') and r.get('correct') is False),
            'false_negative': sum(1 for r in rows if r.get('goal_critic_success') is False and r.get('correct') is True),
        },
        'success_at': summarize(intents)['success_at'],
        'failure_types': summarize(intents)['failure_types'],
        'oscillations': summarize(intents)['oscillations'],
        'mean_elapsed': (sum(row['elapsed'] for row in rows) / len(rows)) if rows else None,
    }


def main() -> None:
    print(json.dumps(build_report(rejudge(load(sys.argv[1:]))), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
