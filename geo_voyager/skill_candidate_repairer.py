from typing import Sequence

from .default_fallback import introduced_fallbacks
from .id_type_literals import id_type_comparisons
from .local_aggregation_contract import local_aggregation_violations
from .skill_candidate import entry_problems
from .execution_attempt import ExecutionAttempt
from .execution_failure import ExecutionFailure, bounded_output
from .intent import Intent
from .observation_context import describe_observations
from .repair_context import attempt_history_text, failing_line_excerpt
from .llama_client import LlamaClient
from .services import load_service_graph
from .skill_candidate import SkillCandidate
from .skill_candidate_generator import _parse_candidate


RESAMPLE_BASE_TEMPERATURE = 0.2
UNCHANGED_NOTE = ('\n前回の出力は元のコードと同一だった。同一のコードは同じエラーを再現するだけである。'
                  '失敗した行を必ず書き換えること。\n')


def _default_note(hidden: list[str]) -> str:
    return ('\n直前の出力は、必須の値が無いことを既定値や except で隠す書き方を新しく入れた: ' + ', '.join(hidden) + '。'
            'これは認めない。Services の説明と Observation の schema にある正しいキーに直す。直せないなら例外のままにする。\n')


def _id_type_note(guesses: list[str]) -> str:
    return ('\n直前の出力は、契約を破っている書き方を残した: ' + ', '.join(guesses) + '。'
            'id_type を固定の文字列と比べない（外れると何も起きずに誤った値になる。intent_target["id_value"] をそのまま使う。'
            'Overpass の area は int(intent_target["id_value"]) + 3600000000）。'
            '測定値の欠落を get の既定値で代用しない。Observation を番号や位置で選ばず、name と ID で選ぶ。\n')


def _normalized(code: str) -> str:
    lines = (line.rstrip() for line in code.splitlines())
    return '\n'.join(line for line in lines if line.strip() and not line.lstrip().startswith('#'))


class SkillCandidateRepairer:
    def __init__(self, llm_client: LlamaClient | None = None, max_resamples: int = 0,
                 max_default_retries: int = 2) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()
        self.max_resamples = max_resamples
        # A repair that hides a missing required value behind a default is asked again this many times, then refused.
        self.max_default_retries = max_default_retries
        # What each refused proposal had added, one list per proposal, kept for the record.
        self.rejected_fallbacks: list[list[str]] = []

    def repair(self, intent: Intent, candidate: SkillCandidate,
               failure: ExecutionFailure,
               history: Sequence[ExecutionAttempt] = ()) -> SkillCandidate:
        graph = load_service_graph()
        services = '\n'.join(f'{service.id}: {service.protocol}: {service.description}'
                             for service in [graph.get(id) for id in intent.service_ids])
        prompt = (
            '失敗した Python Candidate を直接修正してください。Intent を変更しない。\n'
            'API/service を勝手に追加しない。hardcoded answer を入れない。\n'
            '完全な Candidate を再出力する。explanation/chat は不要。\n'
            '標準 Python と登録済み Primitive のみ使用。外部 URL へ直接アクセスしない。\n'
            'Control Primitive contract（geo_voyager.control_primitives から明示的に import）:\n'
            'connect_duckdb(): DuckDB connection。\n'
            'dataset_url(dataset_id): Gateway URL。dataset_id は実行環境から与えられる。\n'
            'load_admin_units(dataset_id, connection, area=None): relation(code5,name,population)。area="東京都23区" 対応。\n'
            'load_stations(dataset_id, connection): relation(name,latitude,longitude)。\n'
            'call_service(service_id, *, path="", params=None, body=None, content_type=None) -> str。'
            'params は dict[str,str]、body=None は GET、それ以外は POST。body は str のまま渡す。encode して bytes にしてはいけない。返答は text。JSON は json.loads。\n'
            '元のコードが関数だけでできていれば、その形を保つ: import と関数の定義だけを書き、関数を呼ぶ行や print は書かない（実行環境が最後の関数を呼び、戻り値を JSON で出力する）。'
            '結果は return で返す。関数名と引数は変えない。環境変数・秘密情報を出力しない。\n'
            '出力形式のみ:\n説明:\n<description>\n---\nコード:\n```python\n<complete code>\n```\n\n'
            f'Intent:\n{intent.text}\n前段 Observation:\n{describe_observations(intent.previous_observations)}\n'
            'previous_observations は実行時 list[str]。intent_text は実行時の現在 Intent。結果をコードに固定せず解析する。\n'
            '前段データや対象番号を貼り込まない。previous_observations を上書きしない。json.loads(previous_observations[index]) を使う。\n'
            f'Dataset ids:\n{intent.dataset_ids}\nServices:\n{services}\n'
            f'元 description:\n{candidate.description}\n元 code:\n{candidate.code}\n'
            f'stdout:\n{bounded_output(failure.stdout)}\nstderr:\n{bounded_output(failure.stderr)}\n'
            f'exit code: {failure.exit_code}\n'
            f'{_history_section(candidate, failure, history)}'
            '必須フィールド（API や Observation の schema にあるキー）が無くて KeyError や欠落になったときは、Services の説明にある実際の API の応答と、'
            '前段 Observation の schema を確認して、正しいキー名に直す。.get(キー, 0)、.get(キー, "")、.get(キー, [])、.get(キー) のような既定値で隠さない'
            '（except で握りつぶすのも同じ）。必須の値が無いときは例外のままにする。直した後も、必須フィールドは [] アクセスか明示的な assert で検証する。\n'
            '最後の制約: 説明本文は元 description と同じ分析操作・対象範囲・出力を保つ。'
            '説明に SyntaxError やバグ修正の説明を書かない。元の分析を行う完全なコードを返す。空の結果を自分で raise した場合は直前の JSON の取り出し方を API contract と照合する。失敗の根本原因の行を実際に変更し、壊れた元コードをそのまま返さない。'
        )
        repaired = self._generate(prompt, RESAMPLE_BASE_TEMPERATURE)
        resamples = retries = 0
        while True:
            if resamples < self.max_resamples and _normalized(repaired.code) == _normalized(candidate.code):
                resamples += 1
                repaired = self._generate(prompt + UNCHANGED_NOTE, RESAMPLE_BASE_TEMPERATURE + 0.2 * resamples)
                continue
            hidden = introduced_fallbacks(candidate.code, repaired.code, failure.stderr)
            guesses = id_type_comparisons(repaired.code) if intent.target is not None and intent.target.resolved else []
            guesses += local_aggregation_violations(repaired.code, len(intent.previous_observations)) if intent.requires_context else []
            # code written as a function stays a function the environment can call
            guesses += entry_problems(repaired.code) if not entry_problems(candidate.code) else []
            if not hidden and not guesses:
                return repaired
            self.rejected_fallbacks.append(hidden + guesses)
            if retries >= self.max_default_retries:
                # Keep the original code: the run fails the same way and the failure stays visible, which is
                # better than a run that succeeds with a value the API never gave.
                return candidate
            retries += 1
            repaired = self._generate(prompt + (_default_note(hidden) if hidden else '') + (_id_type_note(guesses) if guesses else ''),
                                      RESAMPLE_BASE_TEMPERATURE + 0.2 * retries)

    def _generate(self, prompt: str, temperature: float) -> SkillCandidate:
        return _parse_candidate(self.llm_client.generate(
            prompt, temperature=temperature, enable_thinking=True, max_tokens=3072,
            reasoning_budget_tokens=1024, assistant_prefix='説明:\n',
            system_prompt=(
                'You repair Python code. Fix the direct failure and preserve unrelated working code. '
                'Preserve the original description and its operation, scope and output; never describe the bug fix. '
                'For empty query results, check literal and field contracts to fix the cause. '
                'Description must be one sentence describing the reusable operation, not an explanation of the bug. '
                'Return complete executable code, no comments, no discussion, no repeated analysis. '
                'Follow the API contract literally. Do not invent response fields or output formats. '
                'Never hide a missing required field behind a default (.get with 0, "", [] or None) or an except that swallows it: '
                'fix the key from the real schema, or leave the error. '
                'Use runtime previous_observations and intent_text; never paste answers or target IDs. '
                'Exact format:\n説明:\n<one sentence>\n---\nコード:\n```python\n<complete code>\n```'
            ),
        ))


def _history_section(candidate: SkillCandidate, failure: ExecutionFailure,
                     history: Sequence[ExecutionAttempt]) -> str:
    if not history:
        return ''
    excerpt = failing_line_excerpt(candidate.code, failure)
    section = f'失敗した行（>> が実際に失敗した行）:\n{excerpt}\n' if excerpt else ''
    return (section + f'試行履歴:\n{attempt_history_text(history)}\n'
            '同じエラーが続くときは前回と同じ修正を繰り返さない。エラーが指す行の前提'
            '（前段 Observation の型、サービス応答の形式、クエリの header）を疑う。\n')
