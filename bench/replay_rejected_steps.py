"""Ask the step Critic again about stored steps that printed an Observation but were rejected, with and without one extra rule.

    .venv/bin/python -m bench.replay_rejected_steps RESULTS.jsonl [RESULTS.jsonl ...]

The extra rule is inserted just before the Intent. Earlier Observations are not given, as in bench.replay_step_critic.
"""
import json, sys, glob
from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.llama_client import LlamaClient
from geo_voyager.observation import Observation
from geo_voyager.services import load_service_graph
from geo_voyager.target_ref import TargetRef

RULE = ('出力のキー名が Intent に書かれた名前と違っても、要求された値が意味の分かるキーで出力されていれば、キー名だけを理由に失敗にしない'
        '（実行環境の関数は、件数を count、条件を tag のような決まったキーで出力する）。値そのものが無い、または別の値なら失敗。\n')

class Injecting:
    def __init__(self, inner, on): self.inner, self.on = inner, on
    def generate(self, prompt, **kw):
        if self.on: prompt = prompt.replace('\n\nIntent:\n', '\n' + RULE + '\nIntent:\n', 1)
        return self.inner.generate(prompt, **kw)

known = {s.id for s in load_service_graph().all()}
base = LlamaClient()
rows = []
for path in sys.argv[1:]:
    for line in open(path):
        r = json.loads(line)
        for s in r['steps']:
            if s['observation'] and s['critic_success'] is False:
                rows.append((path.split('/')[-2], r['id'], s))
print(len(rows), 'rejected steps that ran', flush=True)
out = []
for run, gid, s in rows:
    services = tuple(x for x in s['resources'] if x in known)
    datasets = tuple(x for x in s['resources'] if x not in known)
    t = s.get('target_ref')
    target = TargetRef(**t) if t else None
    intent = Intent(s['intent'], dataset_ids=datasets, service_ids=services or (() if datasets else ('overpass',)),
                    requires_context=s['local'], target=target)
    verdicts = []
    for on in (False, True):
        c = Critic(Injecting(base, on)).check(intent, [Observation(s['observation'])])
        verdicts.append((c.success, c.reason[:160]))
    res = {'run': run, 'goal': gid, 'step': s['step'], 'intent': s['intent'][:160], 'obs': s['observation'][:160],
           'before': verdicts[0], 'after': verdicts[1]}
    out.append(res)
    print(json.dumps(res, ensure_ascii=False), flush=True)
