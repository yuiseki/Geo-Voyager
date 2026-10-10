"""Ask the local model, given the Generator's real prompt, to explain the harness instead of writing code.

    PYTHONPATH=. .venv/bin/python -m bench.probe_harness_understanding SKILL_LIBRARY_DIR [--runs 3]

The prompt is exactly what SkillCandidateGenerator sends for one Intent (港区の病院の数) with two saved Skills shown
(get_osm_relation_id and count_osm_amenity_cafe, as a carried-over library holds them). Only the request at the end
changes: instead of code, five questions about how the code runs and how Skills are used. The answers show what the
model takes the harness to be. A few model calls, no benchmark.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import Mock

from geo_voyager.intent import Intent
from geo_voyager.llama_client import LlamaClient
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.target_ref import TargetRef

INTENT = Intent('港区内の amenity=hospital の地物数', service_ids=('overpass',), target=TargetRef('港区', 'relation_id', '1761717'))
SHOWN = ('get_osm_relation_id', 'count_osm_amenity_cafe')
QUESTIONS = '''

今回はコードを書かないでください。代わりに、上の説明を読んで、次の 5 つの質問に日本語で、番号をつけて答えてください。
Q1. あなたが書くコードは、どのように実行されますか。誰が、何を、どの値を渡して呼びますか。
Q2. 上に示された get_osm_relation_id と count_osm_amenity_cafe は何ですか。この Intent のコードでそれらをどう使えますか。使うときに import や定義は必要ですか。
Q3. あなたが書いた関数は、実行が成功した後どうなりますか。後の別の Intent（例: 新宿区の amenity=hotel の地物数）は、それをどう使えますか。
Q4. 関数の引数には何を書けますか。intent_target 以外に、amenity=hospital のような条件を関数に渡す方法はありますか。
Q5. この Intent のために、新しい関数を書くべきですか、上の関数を呼ぶべきですか。理由も答えてください。
'''


def captured_prompt(library: SkillLibrary) -> tuple[str, dict]:
    client = Mock()
    client.generate.return_value = ('説明:\nx\n---\nコード:\n```python\ndef f(intent_target):\n    """x"""\n    return 1\n```')
    SkillCandidateGenerator(client).generate(INTENT, [library.get(name) for name in SHOWN])
    return client.generate.call_args.args[0], dict(client.generate.call_args.kwargs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('library')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--out', default=None)
    args = parser.parse_args()
    prompt, options = captured_prompt(SkillLibrary(Path(args.library).expanduser()))
    options.pop('assistant_prefix', None)
    options['system_prompt'] = ('You are a precise Python programmer who is about to work in this environment. '
                                'This time, do not write code: answer the questions about the environment in Japanese.')
    answers = []
    for run in range(1, args.runs + 1):
        answer = LlamaClient().generate(prompt + QUESTIONS, **options)
        answers.append(answer)
        print(f'===== run {run}\n{answer}\n', flush=True)
    if args.out:
        Path(args.out).write_text(json.dumps({'prompt': prompt + QUESTIONS, 'options': options, 'answers': answers},
                                             ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
