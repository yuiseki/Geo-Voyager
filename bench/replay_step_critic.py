"""Ask the step Critic again about stored steps of bench.run_adaptive that ask for a comparison, a selection or a total.

    .venv/bin/python -m bench.replay_step_critic RESULTS.jsonl [RESULTS.jsonl ...]

Only steps that ran and printed something are asked again, with their Intent and Observation as recorded. The
Observations of earlier steps are not given (the run records do not keep them per step), so a verdict can differ
from the one in the run. Prints the verdicts, then a JSON list, for a before/after comparison of the prompt.
"""
import json
import re
import sys
from pathlib import Path

from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.llama_client import LlamaClient
from geo_voyager.observation import Observation
from geo_voyager.services import load_service_graph

ASKS_FOR_AN_ANSWER = re.compile(r'比較|多い|少ない|最大|最小|最も|合計|上位|選ぶ|特定')


def main() -> None:
    critic = Critic(LlamaClient())
    known = {service.id for service in load_service_graph().all()}
    out = []
    for name in sys.argv[1:]:
        path = Path(name).expanduser()
        for line in path.read_text().splitlines():
            row = json.loads(line)
            for step in row['steps']:
                if not (step['succeeded'] and step['observation'] and ASKS_FOR_AN_ANSWER.search(step['intent'])):
                    continue
                services = tuple(r for r in step['resources'] if r in known)
                datasets = tuple(r for r in step['resources'] if r not in known)
                intent = Intent(step['intent'], dataset_ids=datasets, service_ids=services or (() if datasets else ('overpass',)),
                                requires_context=step['local'])
                critique = critic.check(intent, [Observation(step['observation'])])
                result = {'run': f"{path.parent.name}/{row['id']}", 'step': step['step'], 'intent': step['intent'],
                          'observation': step['observation'][:200], 'recorded': step['critic_success'], 'now': critique.success,
                          'reason': critique.reason}
                out.append(result)
                print(result['run'], result['step'], '| recorded', result['recorded'], '| now', result['now'], '|',
                      step['intent'][:50], '|', step['observation'][:70], flush=True)
    print('steps', len(out), '| accepted now', sum(r['now'] for r in out))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
