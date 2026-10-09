"""Ask the current Critic again about stored steps, with no sandbox and no other model call.

    .venv/bin/python -m bench.replay_critic RESULTS.jsonl [RESULTS.jsonl ...] [--controls 25]

Targets are the steps where the Critic accepted a wrong final answer (every step ran, the Goal judge said no).
Controls are final steps of runs the Goal judge accepted. A change to the Critic prompt should reject the
targets without rejecting the controls. The stored observations and Intents are used as recorded.
"""
import argparse
import json
from pathlib import Path

from bench.replay_semantic import build_intent
from bench.report import load, rejudge
from bench.taxonomy import classify
from geo_voyager.critic import Critic
from geo_voyager.llama_client import LlamaClient
from geo_voyager.observation import Observation


def final_step(path: Path, row: dict) -> tuple[dict, list[Observation]] | None:
    report = path.parent / f"{row['id']}.r{row['round']}" / 'goal_report.json'
    if not report.exists():
        return None
    data = json.loads(report.read_text())
    if not data['executions']:
        return None
    execution = data['executions'][-1]
    attempts = execution['attempts']
    observations = execution['observations'] or (attempts[-1]['observations'] if attempts else [])
    return data['intents'][-1], [Observation(o['text']) for o in observations]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('results', nargs='+')
    parser.add_argument('--controls', type=int, default=25)
    args = parser.parse_args()
    critic = Critic(LlamaClient())
    targets, controls = [], []
    for name in args.results:
        path = Path(name).expanduser()
        for row in rejudge(load([str(path)])):
            verdict = classify(row)
            step = final_step(path, row)
            if step is None or not step[1]:
                continue
            if verdict and verdict['category'] in ('semantic-completion', 'aggregation') and 'critic rejected' not in verdict['evidence']:
                targets.append((f"{path.parent.name}/{row['id']}.r{row['round']}", step))
            elif verdict is None and row.get('correct'):
                controls.append((f"{path.parent.name}/{row['id']}.r{row['round']}", step))
    out = {'targets': [], 'controls': []}
    for label, group in (('targets', targets), ('controls', controls[:args.controls])):
        for name, (raw, observations) in group:
            critique = critic.check(build_intent(raw), observations)
            out[label].append({'run': name, 'success': critique.success, 'reason': critique.reason})
            print(label, name, 'accepted' if critique.success else 'rejected', '|', critique.reason[:110], flush=True)
    print('targets rejected:', sum(not r['success'] for r in out['targets']), '/', len(out['targets']),
          '| controls rejected:', sum(not r['success'] for r in out['controls']), '/', len(out['controls']))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
