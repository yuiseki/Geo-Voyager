from .execution_failure import ExecutionFailure, bounded_output
from .intent import Intent
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
            'params は dict[str,str]、body=None は GET、それ以外は POST。返答は text。JSON は json.loads。\n'
            '最終結果を stdout に出す。環境変数・秘密情報を出力しない。\n'
            '出力形式のみ:\n説明:\n<description>\n---\nコード:\n```python\n<complete code>\n```\n\n'
            f'Intent:\n{intent.text}\n前段 Observation:\n{[obs.text for obs in intent.previous_observations]}\n'
            'previous_observations は実行時 list[str]。intent_text は実行時の現在 Intent。結果をコードに固定せず解析する。\n'
            f'Dataset ids:\n{intent.dataset_ids}\nServices:\n{services}\n'
            f'元 description:\n{candidate.description}\n元 code:\n{candidate.code}\n'
            f'stdout:\n{bounded_output(failure.stdout)}\nstderr:\n{bounded_output(failure.stderr)}\n'
            f'exit code: {failure.exit_code}'
        )
        return _parse_candidate(self.llm_client.generate(
            prompt, temperature=0.0, enable_thinking=True, max_tokens=4096,
            reasoning_budget_tokens=1024, assistant_prefix='説明:\n',
        ))
