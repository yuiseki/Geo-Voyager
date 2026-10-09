"""Ask the real runtime repairer to repair the KeyError that once ended in `.get("count_all", 0)`. A few calls, no benchmark.

    .venv/bin/python -m bench.replay_repair_fallback [N]

The candidate is the code a model wrote for 'the top 3 values of the cuisine key' that read `count_all` from a
key/values answer. The failure is the KeyError it raised. The repairer is the real one with the real model, so what is
measured is what the model does when it is handed that failure, and what the check does about it. The first reply is
read before the check (a client wrapper records it), so the rate at which the model reaches for a default is visible.
"""
import json
import sys

from geo_voyager.default_fallback import introduced_fallbacks
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.llama_client import LlamaClient
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer

CODE = '''from geo_voyager.control_primitives import call_service
import json

resp = call_service("taginfo", path="/api/4/key/values", params={"key": "cuisine", "sortname": "count", "sortorder": "desc", "page": "1", "rp": "3"})
data = json.loads(resp)
items = data["data"]
if not items:
    raise ValueError("No cuisine values found")
top3 = [{"value": item["value"], "count": item["count_all"]} for item in items[:3]]
print(json.dumps(top3))'''
STDERR = 'Traceback (most recent call last):\n  File "<stdin>", line 15, in <module>\n  File "<candidate>", line 9, in <module>\nKeyError: \'count_all\''


class Recording:
    def __init__(self, client):
        self.client, self.replies = client, []

    def generate(self, *args, **kwargs):
        reply = self.client.generate(*args, **kwargs)
        self.replies.append(reply)
        return reply


def main() -> None:
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    intent = Intent('Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。', service_ids=('taginfo',))
    summary = []
    for number in range(1, runs + 1):
        llm = Recording(LlamaClient())
        repairer = SkillCandidateRepairer(llm)
        result = repairer.repair(intent, SkillCandidate(CODE, '上位3つの値と使用数を取得する'),
                                 ExecutionFailure('Generated Python execution failed', '', STDERR, 73))
        first = llm.replies[0]
        first_code = first.split('```python\n', 1)[1].split('```', 1)[0].strip() if '```python' in first else ''
        row = {'run': number, 'model_calls': len(llm.replies),
               'first_reply_hid_the_value': bool(introduced_fallbacks(CODE, first_code, STDERR)),
               'first_reply': [line.strip() for line in first_code.splitlines() if 'count' in line][:2],
               'refused': getattr(repairer, 'rejected_fallbacks', []), 'kept_original': result.code.strip() == CODE.strip(),
               'final_uses_count_key': 'item["count"]' in result.code or "item['count']" in result.code,
               'final_has_default': bool(introduced_fallbacks(CODE, result.code, STDERR))}
        summary.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print('first replies that hid the value:', sum(r['first_reply_hid_the_value'] for r in summary), '/', runs,
          '| final code uses the right key:', sum(r['final_uses_count_key'] for r in summary), '/', runs,
          '| final code has a default:', sum(r['final_has_default'] for r in summary), '/', runs)


if __name__ == '__main__':
    main()
