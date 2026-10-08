from .execution_failure import ExecutionFailure, bounded_output
from .intent import Intent
from .observation_context import describe_observations
from .llama_client import LlamaClient
from .services import load_service_graph
from .skill_candidate import SkillCandidate
from .skill_candidate_generator import _parse_candidate


class SkillCandidateRepairer:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def repair(self, intent: Intent, candidate: SkillCandidate,
               failure: ExecutionFailure) -> SkillCandidate:
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
            '最終結果を stdout に出す。環境変数・秘密情報を出力しない。\n'
            '出力形式のみ:\n説明:\n<description>\n---\nコード:\n```python\n<complete code>\n```\n\n'
            f'Intent:\n{intent.text}\n前段 Observation:\n{describe_observations(intent.previous_observations)}\n'
            'previous_observations は実行時 list[str]。intent_text は実行時の現在 Intent。結果をコードに固定せず解析する。\n'
            '前段データや対象番号を貼り込まない。previous_observations を上書きしない。json.loads(previous_observations[index]) を使う。\n'
            f'Dataset ids:\n{intent.dataset_ids}\nServices:\n{services}\n'
            f'元 description:\n{candidate.description}\n元 code:\n{candidate.code}\n'
            f'stdout:\n{bounded_output(failure.stdout)}\nstderr:\n{bounded_output(failure.stderr)}\n'
            f'exit code: {failure.exit_code}\n'
            '最後の制約: 説明本文は元 description と同じ分析操作・対象範囲・出力を保つ。'
            '説明に SyntaxError やバグ修正の説明を書かない。元の分析を行う完全なコードを返す。空の結果を自分で raise した場合は直前の JSON の取り出し方を API contract と照合する。失敗の根本原因の行を実際に変更し、壊れた元コードをそのまま返さない。'
        )
        return _parse_candidate(self.llm_client.generate(
            prompt, temperature=0.2, enable_thinking=True, max_tokens=3072,
            reasoning_budget_tokens=1024, assistant_prefix='説明:\n',
            system_prompt=(
                'You repair Python code. Fix the direct failure and preserve unrelated working code. '
                'Preserve the original description and its operation, scope and output; never describe the bug fix. '
                'For empty query results, check literal and field contracts to fix the cause. '
                'Description must be one sentence describing the reusable operation, not an explanation of the bug. '
                'Return complete executable code, no comments, no discussion, no repeated analysis. '
                'Follow the API contract literally. Do not invent response fields or output formats. '
                'Use runtime previous_observations and intent_text; never paste answers or target IDs. '
                'Exact format:\n説明:\n<one sentence>\n---\nコード:\n```python\n<complete code>\n```'
            ),
        ))
