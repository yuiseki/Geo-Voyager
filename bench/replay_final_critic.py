"""Ask the final Critic again about stored step-by-step runs, with and without the final-check instruction.

    .venv/bin/python -m bench.replay_final_critic RESULTS.jsonl [RESULTS.jsonl ...]

A row is a run of bench.run_adaptive. The final Critic sees the Goal and the Observations of the steps that
succeeded, as GoalExecutor gives them. 'correct' is the Goal judge's verdict on the last Observation, so a run
whose Goal needs a comparison that no step printed is 'correct' False even when every count is right.
"""
import json
import sys
from pathlib import Path

from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.llama_client import LlamaClient
from geo_voyager.observation import Observation
from geo_voyager.services import load_service_graph


def final_input(row: dict) -> tuple[Intent, list[Observation]] | None:
    steps = [s for s in row['steps'] if s['succeeded'] and s['critic_success'] and s['observation']]
    if not steps:
        return None
    known = {service.id for service in load_service_graph().all()}
    resources = [r for s in steps for r in s['resources']]
    services = tuple(dict.fromkeys(r for r in resources if r in known))
    datasets = tuple(dict.fromkeys(r for r in resources if r not in known))
    if not services and not datasets:
        return None
    return (Intent(row['goal'], dataset_ids=datasets, service_ids=services, requires_context=True),
            [Observation(s['observation']) for s in steps])


def main() -> None:
    critic = Critic(LlamaClient())
    rows = []
    for name in sys.argv[1:]:
        for line in Path(name).expanduser().read_text().splitlines():
            row = json.loads(line)
            if row.get('correct') is not None and row['steps']:
                rows.append((Path(name).parent.name, row))
    out = []
    for source, row in rows:
        item = final_input(row)
        if item is None:
            continue
        before = critic.check(*item, final=False)
        after = critic.check(*item, final=True)
        result = {'run': f"{source}/{row['id']}", 'stop': row['stop_reason'], 'correct': row['correct'],
                  'before': before.success, 'after': after.success, 'reason_after': after.reason}
        out.append(result)
        print(result['run'], '| stop', result['stop'], '| correct', result['correct'], '| accepted before', before.success,
              '| after', after.success, '|', after.reason[:90], flush=True)
    for correct in (True, False):
        group = [r for r in out if r['correct'] == correct]
        print(f'correct={correct}: {len(group)} runs | accepted before {sum(r["before"] for r in group)} | after {sum(r["after"] for r in group)}')
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
