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

from geo_voyager.critique import Critique
from geo_voyager.datasets import load_dataset_graph
from geo_voyager.services import load_service_graph
from geo_voyager.skill_candidate import called_service_ids, read_datasets
from geo_voyager.llama_client import LlamaClient

ANCHOR = '入力の Intent と Observation だけで要求した出力が得られたか判定する。外部知識で答えを推測・追加しない。Intent にない期待件数を仮定しない。\n'
# Hypothesis 2: the model's knowledge of single places (which wards touch) was wrong 7 times and right 0; its sense
# of scale (no station in the 23 wards) was right 12 times.
PLACE_FACTS = ('個々の地物についての事実（どの区とどの区が接するか、ある名前が一覧に入るべきか）を、自分の知識で否定・補完して失敗の理由にしない。'
               'データの定義（陸か海を含むか、どの版か）で答えが変わるため。値が 0 や空のこと、件数の桁が明らかに合わないことは疑ってよい。\n')
CODE_HEADER = ('\n\nこの Observation を出力したコード（どう測ったかの根拠として読む。'
               'コードが Intent の対象の一部だけを測っている、または Intent と違う条件で測っているなら失敗。'
               'コードが Intent どおりに測っているなら、値の正しさを自分の知識で否定しない）:\n')


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


def resource_notes(code: str) -> str:
    """What the services and datasets the code reads are, as the Planner and the Generator are told."""
    services = load_service_graph()
    datasets = load_dataset_graph()
    lines = [f'{service_id}: {services.get(service_id).description}' for service_id in sorted(called_service_ids(code))]
    lines += [f'{dataset_id}: {datasets.get(dataset_id).description}' for dataset_id in sorted(read_datasets(code))
              if dataset_id in {dataset.id for dataset in datasets.all()}]
    return '\n'.join(lines)


RESOURCES_HEADER = '\n\nコードが読んだサービスとデータの説明（コードが Intent の対象を正しく選んだかを照合するために読む）:\n'


def changed(prompt: str, variant: str, path: Path) -> str:
    if variant in ('rule', 'code+rule', 'all'):
        if ANCHOR not in prompt:
            raise ValueError(f'{path}: the anchor of the rule is not in the prompt')
        prompt = prompt.replace(ANCHOR, ANCHOR + PLACE_FACTS)
    if variant in ('code', 'code+rule', 'all') and 'Goal 全体の最終判定' not in prompt:
        code = producing_code(path)
        if code is not None:
            prompt += CODE_HEADER + code
            notes = resource_notes(code) if variant == 'all' else ''
            if notes:
                prompt += RESOURCES_HEADER + notes
    return prompt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', required=True)
    parser.add_argument('--variant', required=True, choices=['base', 'rule', 'code', 'code+rule', 'all'])
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
            critique = Critique.from_text(reply)
            verdict = '成功' if critique.success else '失敗'
            ok = verdict == case['expected']
            right, wrong = right + ok, wrong + (not ok)
            row = {**case, 'variant': args.variant, 'verdict': verdict, 'right': ok, 'reason': critique.reason,
                   'elapsed': round(time.time() - started, 1)}
            results.write(json.dumps(row, ensure_ascii=False) + '\n')
            results.flush()
            print(case['case'], case['expected'], verdict, 'ok' if ok else 'WRONG', critique.reason[:80], flush=True)
    summary = {'variant': args.variant, 'right': right, 'wrong': wrong}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
