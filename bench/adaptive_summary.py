"""Summarize a round of bench.run_adaptive: what was answered, where the rest stopped, and which checks fired.

    .venv/bin/python -m bench.adaptive_summary RESULTS.jsonl

The outcome of a run is one of:
  correct              the run ended with DONE and the Goal judge accepted the last Observation
  stopped:<reason>+    the loop ended without DONE, yet the judge accepts the last Observation (an answer the loop did not confirm)
  wrong_accepted       the run ended with DONE and the final Critic passed it, but the Goal judge did not
  stopped:<reason>     the loop ended without DONE (max_steps, repeated_intent, planner_failure, final_critic_failed, ...)
  unmeasured           no oracle answer
The checks counted are the deterministic ones: Planner refusals (by the start of their reason), code-contract
refusals of the Generator, refusals in runtime repair, and final Critic failures.
"""
from collections import Counter
import json
import sys
from pathlib import Path


def outcome(row: dict) -> str:
    if row.get('correct') is None:
        return 'unmeasured'
    if row['stop_reason'] == 'done':
        return 'correct' if row['correct'] else 'wrong_accepted'
    return f"stopped:{row['stop_reason']}" + ('+' if row['correct'] else '')


def planner_refusal_kind(reason: str) -> str:
    for marker, kind in (('API の詳細', 'api_detail'), ('「対象:', 'target_not_entity'), ('ambiguous', 'ambiguous_target'),
                         ('more than one 対象', 'two_targets'), ('Plan must', 'format'), ('Unexpected plan fields', 'format')):
        if marker in reason:
            return kind
    return 'other'


def checks(row: dict) -> Counter:
    counted = Counter()
    for event in row['events']:
        if event['kind'] == 'planner_failure':
            counted[f"planner_refused:{planner_refusal_kind(event.get('reason', ''))}"] += 1
        elif event['kind'] == 'final_critic_failure':
            counted['final_critic_failure'] += 1
    for step in row['steps']:
        failure = step.get('failure') or ''
        if 'breaks the code contract' in failure or 'compares id_type' in failure:
            counted['generator_contract_refused'] += 1
    counted['repair_refusals'] += len(row.get('rejected_fallbacks') or [])
    return counted


def main() -> None:
    rows = [json.loads(line) for line in Path(sys.argv[1]).expanduser().read_text().splitlines() if line.strip()]
    outcomes = Counter(outcome(row) for row in rows)
    total = Counter()
    print(f'{len(rows)} runs')
    for row in rows:
        fired = checks(row)
        total.update(fired)
        shown = ', '.join(f'{k}={v}' for k, v in sorted(fired.items()) if v)
        print(f"{row['id']:28s} {outcome(row):24s} steps={len(row['steps'])} planner_calls={row['planner_calls']} "
              f"{row['elapsed']:6.1f}s {shown}")
    print('outcomes:', dict(outcomes))
    print('checks fired:', {k: v for k, v in sorted(total.items()) if v})


if __name__ == '__main__':
    main()
