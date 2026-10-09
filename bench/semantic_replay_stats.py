"""Pick the saved failures a semantic repair could have acted on, and count what a replay did.

A semantic repair fires only after a run that succeeded and was rejected by the Critic. So a case is
a saved Goal run whose first wrong step is a semantic-completion failure of that kind. Failures where
the Critic accepted a wrong answer are left out: nothing triggers a repair there.
"""
from collections import Counter
import json
from pathlib import Path

from bench.report import load, rejudge
from bench.taxonomy import classify

CATEGORIES = ('rescued', 'still_failing', 'unchanged', 'vibration', 'hardcoded_rejected', 'invalid', 'worsened')
_BY_STATUS = {'unchanged': 'unchanged', 'vibration': 'vibration', 'hardcoded': 'hardcoded_rejected', 'invalid': 'invalid'}


def select_cases(results_path: Path) -> tuple[list[dict], dict]:
    cases, skipped = [], Counter()
    for row in rejudge(load([str(results_path)])):
        verdict = classify(row)
        if not verdict or verdict['category'] != 'semantic-completion':
            continue
        if 'critic rejected a step that ran' not in verdict['evidence']:
            skipped['the Critic accepted the wrong answer'] += 1
            continue
        run = f"{row['id']}.r{row['round']}"
        report = results_path.parent / run / 'goal_report.json'
        if not report.exists():
            skipped['no goal report'] += 1
            continue
        data = json.loads(report.read_text())
        index = verdict['first_wrong_step'] - 1
        execution = data['executions'][index]
        attempts = execution['attempts']
        if not attempts or attempts[-1]['failure'] is not None or execution['critique']['success']:
            skipped['the step did not match'] += 1
            continue
        observations = [o['text'] for o in attempts[-1]['observations']] or [o['text'] for o in execution['observations']]
        cases.append({
            'run': run, 'source': results_path.parent.name, 'goal_id': row['id'], 'round': row['round'],
            'step': index + 1, 'intent': data['intents'][index], 'code': attempts[-1]['code'],
            'observations': observations, 'reason': execution['critique']['reason'],
            'history': [attempt['code'] for attempt in attempts], 'oracle': row.get('oracle'),
            'critic_thinking': row.get('critic_thinking', False),
        })
    return cases, dict(skipped)


def output_keys(text: str) -> set[str] | None:
    """The keys of a JSON object output, or of the objects in a JSON list. None when there are none."""
    try:
        value = json.loads(text)
    except ValueError:
        return None
    if isinstance(value, dict):
        return set(value)
    if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
        return set().union(*value)
    return None


def refresh_keys(result: dict) -> dict:
    """Recompute which output keys a repair removed or added, from the stored before and after texts."""
    old, new = (output_keys(result[name]) if result.get(name) else None for name in ('before', 'after'))
    if old is None or new is None:
        return dict(result, keys_removed=[], keys_added=[])
    return dict(result, keys_removed=sorted(old - new), keys_added=sorted(new - old))


def categorize(result: dict) -> str:
    if result['status'] != 'proposed':
        return _BY_STATUS[result['status']]
    if result['execution_failed'] or not result['after']:
        return 'worsened'
    if result['critic_success']:
        return 'rescued'
    if result['after'] == result['before']:
        return 'unchanged'
    return 'worsened' if result['keys_removed'] else 'still_failing'


def summarize(results: list[dict]) -> dict:
    counts = Counter(categorize(result) for result in results)
    summary = {'cases': len(results), **{name: counts.get(name, 0) for name in CATEGORIES}}
    summary['output_keys_changed'] = sum(1 for r in results if r.get('keys_added') or r.get('keys_removed'))
    return summary


def main() -> None:
    """Recompute the summary of a replay from its stored results: python -m bench.semantic_replay_stats replay.jsonl"""
    import sys
    results = [refresh_keys(json.loads(line)) for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    for result in results:
        result['category'] = categorize(result)
    print(json.dumps({'summary': summarize(results), 'results': results}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
