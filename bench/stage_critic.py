"""Stage 4 of a staged run: Critic calls of earlier runs, asked again with a change to the prompt.

    .venv/bin/python -m bench.stage_critic --cases CASES.jsonl --variant NAME --out DIR

CASES.jsonl has one Critic call per line: {"case", "prompt" (an llm_NN_prompt.txt of a run), "expected"
(成功 or 失敗, judged by hand from the data), "note"}. The saved prompt is changed by the variant and sent at
temperature zero, so two variants differ only by the change. A variant stands for a change to geo_voyager.critic
that has not been made yet; the one that wins is then made there, with tests.

DIR gets one line per case in results.jsonl and the counts of right and wrong verdicts.
"""
import argparse
import json
from pathlib import Path
import re
import time

from geo_voyager.critic import CARRIED, CODE_HEADER, PLACE_FACTS, READ_NAMES, RESOURCES_HEADER
from geo_voyager.critique import Critique
from geo_voyager.dataset_references import REFERENCED, critic_text
from geo_voyager.datasets import load_dataset_graph
from geo_voyager.services import load_service_graph
from geo_voyager.skill_candidate import called_service_ids, read_datasets
from geo_voyager.llama_client import LlamaClient

ANCHOR = '入力の Intent と Observation だけで要求した出力が得られたか判定する。外部知識で答えを推測・追加しない。Intent にない期待件数を仮定しない。\n'
# Made in geo_voyager.critic after stage 4 (the variant all) and stage 5 (all+both, hypotheses 3 and 4: an Intent
# names the column to read and the key to output; a relation_id carried from the step before is not of the dataset
# read). A prompt the current Critic wrote already has them.
KEY_ANCHOR = '値そのものが無い、または別の値なら失敗。\n'
# Hypothesis 5: with both, case 29 broke the two lines; told at the end of the prompt to write the two lines only, the
# Critic stopped checking the list and misread it (stage 5). The verdict is now read from the last two lines instead.
# Hypothesis 6 (the small tasks of GeoAI-master-skills, task 15): told what a row of the table is and what the columns the
# code uses mean, the Critic stops failing ward IS NULL as not leaving out the wards' rows (geo_voyager.critic).
VARIANTS = ['base', 'rule', 'code', 'code+rule', 'all', 'all+names', 'all+carried', 'all+both', 'all+both+columns']


def producing_code(prompt_path: Path) -> str | None:
    """The code of the attempt the Critic judged: the last code a model wrote before this call in the same Goal."""
    number = int(re.search(r'llm_(\d+)_prompt', prompt_path.name).group(1))
    for earlier in range(number - 1, 0, -1):
        response = prompt_path.with_name(f'llm_{earlier:02d}_response.txt')
        if not response.exists():
            continue
        match = re.search(r'```python\n(.*?)```', response.read_text(), re.S)
        if match:
            return match.group(1)
    return None


def resource_notes(code: str, columns: bool = False) -> str:
    """What the services and datasets the code reads are, as the Planner and the Generator are told; with columns,
    what a row is and what the columns the code uses mean too."""
    services = load_service_graph()
    datasets = load_dataset_graph()
    lines = [f'{service_id}: {services.get(service_id).description}' for service_id in sorted(called_service_ids(code))]
    lines += [f'{dataset_id}: {datasets.get(dataset_id).description}'
              + (f' {critic_text(dataset_id, code)}' if columns and dataset_id in REFERENCED else '')
              for dataset_id in sorted(read_datasets(code))
              if dataset_id in {dataset.id for dataset in datasets.all()}]
    return '\n'.join(lines)


def with_columns(prompt: str, path: Path) -> str:
    """The prompt with its description of what the code read made again, columns included."""
    if CODE_HEADER not in prompt:
        return prompt
    code = prompt.split(CODE_HEADER, 1)[1].split(RESOURCES_HEADER, 1)[0]
    notes = resource_notes(code, columns=True)
    return prompt.split(RESOURCES_HEADER, 1)[0] + (RESOURCES_HEADER + notes if notes else '')


def changed(prompt: str, variant: str, path: Path) -> str:
    stage4 = variant.split('+')[0] if variant.startswith('all') else variant
    if stage4 in ('rule', 'code+rule', 'all') and PLACE_FACTS not in prompt:
        if ANCHOR not in prompt:
            raise ValueError(f'{path}: the anchor of the rule is not in the prompt')
        prompt = prompt.replace(ANCHOR, ANCHOR + PLACE_FACTS)
    if stage4 in ('code', 'code+rule', 'all') and 'Goal 全体の最終判定' not in prompt and CODE_HEADER not in prompt:
        code = producing_code(path)
        if code is not None:
            prompt += CODE_HEADER + code
            notes = resource_notes(code) if stage4 == 'all' else ''
            if notes:
                prompt += RESOURCES_HEADER + notes
    added = {'all+names': READ_NAMES, 'all+carried': CARRIED, 'all+both': READ_NAMES + CARRIED,
             'all+both+columns': READ_NAMES + CARRIED}.get(variant, '')
    if added and added not in prompt:
        if KEY_ANCHOR not in prompt:
            raise ValueError(f'{path}: the anchor of the key rule is not in the prompt')
        prompt = prompt.replace(KEY_ANCHOR, KEY_ANCHOR + added)
    if variant.endswith('+columns'):
        prompt = with_columns(prompt, path)
    return prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True)
    parser.add_argument('--variant', required=True, choices=VARIANTS)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=False)
    client = LlamaClient()
    right = wrong = 0
    with (out / 'results.jsonl').open('w') as results:
        for line in Path(args.cases).expanduser().read_text().splitlines():
            case = json.loads(line)
            path = Path(case['prompt']).expanduser()
            original = path.read_text()
            # The system prompt of a step with earlier Observations is not in the saved file; it is added the same way.
            system = None
            if '前段 Observation（対象の identity を照合するためのデータ）' in original:
                system = ('Judge only the current returned Observation. Previous observations are reference evidence, '
                          'not the current answer. A correct answer present only in reference data does not make '
                          'the current execution successful. If the returned target/value is incorrect, return 失敗. '
                          'Return exactly 判定: 成功 or 判定: 失敗, then 理由: on the second line.')
            started = time.time()
            reply = client.generate(changed(original, args.variant, path), temperature=0.0, system_prompt=system)
            try:
                critique = Critique.from_text(reply)
                verdict, reason = ('成功' if critique.success else '失敗'), critique.reason
            except ValueError:
                # A reply without the two lines; the Critic raises on it too, so it counts as a wrong verdict.
                verdict, reason = '不正', reply
            ok = verdict == case['expected']
            right, wrong = right + ok, wrong + (not ok)
            row = {**case, 'variant': args.variant, 'verdict': verdict, 'right': ok, 'reason': reason,
                   'elapsed': round(time.time() - started, 1)}
            results.write(json.dumps(row, ensure_ascii=False) + '\n')
            results.flush()
            print(case['case'], case['expected'], verdict, 'ok' if ok else 'WRONG', reason[:80], flush=True)
    summary = {'variant': args.variant, 'right': right, 'wrong': wrong}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
