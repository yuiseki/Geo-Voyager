"""Ask the final Critic again with the exact prompts logged by bench.run_adaptive, with thinking off and on.

    .venv/bin/python -m bench.replay_final_prompts RUN_DIR [RUN_DIR ...]

Each RUN_DIR is a --out of bench.run_adaptive. A prompt is the final Critic's when it carries the final-judgement
sentence. Its last Observation is judged against the oracle stored in RUN_DIR/results.jsonl, with the Goal's own
judge, so every verdict can be scored: a success on a wrong answer, or a failure on a right one, is an error.
"""
import json, sys, time
from pathlib import Path
from bench.goals import GOALS
from geo_voyager.critique import Critique
from geo_voyager.llama_client import LlamaClient

FINAL = 'これは Goal 全体の最終判定'
judges = {goal.id: goal.judge for goal in GOALS}
client = LlamaClient()
for run in map(Path, sys.argv[1:]):
    oracles = {row['id']: row.get('oracle') for row in map(json.loads, open(run / 'results.jsonl'))}
    for prompt_path in sorted(run.glob('*/llm_*_prompt.txt')):
        prompt = prompt_path.read_text()
        if FINAL not in prompt:
            continue
        goal = prompt_path.parent.name.split('_', 1)[1]
        observations = [line[2:] for line in prompt.split('\nObservation:\n', 1)[1].split('\n' + FINAL)[0].splitlines()
                        if line.startswith('- ')]
        right = bool(observations) and oracles.get(goal) is not None and bool(judges[goal](observations[-1], oracles[goal]))
        logged = Critique.from_text(prompt_path.with_name(prompt_path.name.replace('_prompt', '_response')).read_text())
        row = {'run': run.name, 'goal': goal, 'prompt': prompt_path.name, 'answer_right': right,
               'logged': logged.success}
        for name, options in (('off', {}), ('on', dict(enable_thinking=True, max_tokens=4096, reasoning_budget_tokens=1024))):
            started = time.time()
            critique = Critique.from_text(client.generate(prompt, temperature=0.0, **options))
            row[name] = critique.success
            row[name + '_reason'] = critique.reason[:200]
            row[name + '_seconds'] = round(time.time() - started, 1)
        print(json.dumps(row, ensure_ascii=False), flush=True)
