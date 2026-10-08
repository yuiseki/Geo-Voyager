from .intent import Intent
from .llama_client import LlamaClient
from .skill_candidate import SkillCandidate


def _parse_candidate(text: str) -> SkillCandidate:
    lines = text.strip().splitlines()
    if not lines or lines[0] != '説明:' or lines.count('---') != 1:
        raise ValueError('Candidate must contain 説明: and a single --- separator')
    separator = lines.index('---')
    code_block = '\n'.join(lines[separator + 1:]).strip()
    if not code_block.startswith('コード:'):
        raise ValueError('Candidate must contain コード:')
    fenced = code_block.removeprefix('コード:').strip().splitlines()
    if len(fenced) < 2 or fenced[0] != '```python' or fenced[-1] != '```':
        raise ValueError('Candidate code must use a Python code fence')
    description = '\n'.join(lines[1:separator]).strip()
    code_lines = fenced[1:-1]
    code = '\n'.join(code_lines).strip()
    if not description or not code or any(line.startswith('```') for line in code_lines):
        raise ValueError('Candidate description and code must be non-empty and correctly fenced')
    return SkillCandidate(code=code, description=description)


class SkillCandidateGenerator:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def generate(self, intent: Intent) -> SkillCandidate:
        datasets = '\n'.join(f'- {dataset_id}' for dataset_id in intent.dataset_ids)
        prompt = (
            'Intent を完遂する実行可能な Python コードと簡潔な説明を書いてください。\n'
            '関数やクラスの定義は不要です。短いトップレベルのスクリプトを書いてください。\n'
            '利用可能な Control Primitives（geo_voyager.control_primitives から import）:\n'
            '- connect_duckdb(): sandbox 用 DuckDB 接続を返す。with で接続を管理する。\n'
            '- dataset_url(dataset_id): 登録済み行政区 Dataset の Gateway URL を返す。\n'
            '- load_admin_units(dataset_id, connection): Gateway 経由で行政区域の DuckDB relation を返す。\n'
            'relation の列は code5（5桁文字列の行政コード）、name（区域名）、population（整数の人口）。\n'
            '東京23区の code5 は13101〜13123。\n'
            '返り値は DuckDB relation であり pandas DataFrame ではない。\n'
            'relation API: filter(expression) は SQL 条件文字列で絞り込む。\n'
            'order(expression) は SQL の列名と ASC/DESC でソートする。limit(n) は行数を制限する。\n'
            'fetchone() は (code5, name, population) の tuple または None を返す。\n'
            'DataFrame の添字、between、sort_values、head、iloc は使えない。\n\n'
            '制約:\n'
            '- Primitive はグローバルには存在しない。必ずコードで明示的に import する。\n'
            'from geo_voyager.control_primitives import connect_duckdb, load_admin_units\n'
            '- Dataset へのアクセスは Control Primitives のみ使う。\n'
            '- 外部URLを直接使わない。HTTP や read_parquet を直接呼ばない。\n'
            '- 最終結果を stdout に出す。stdout に選択・集計の意味と具体的な回答値を明示する。\n'
            '例えば最小人口なら、最も少ない区を求めたこと、得られた区名と人口を文章で示す。\n'
            '- dataset_id は実行環境から与えられる。既存のグローバル変数を参照するだけにする。\n'
            'dataset_id = ... という代入を書かない。Dataset ids は利用範囲のメタデータでありコードへ埋め込まない。\n'
            '- 再利用可能な分析コードにする。答えの区名や人口を埋め込まない。\n'
            '- 標準 Python と上記 Primitive・DuckDB relation の操作だけで実装する。\n'
            '- UUID 生成や Skill の保存はしない。\n'
            '- 1件だけ生成し、前置きや追記を付けない。\n\n'
            '出力形式と接続部分（分析と stdout を続けて実装してください）:\n'
            '説明:\n調査コードの簡潔な説明\n---\nコード:\n```python\n'
            'from geo_voyager.control_primitives import connect_duckdb, load_admin_units\n'
            'with connect_duckdb() as connection:\n'
            '    units = load_admin_units(dataset_id, connection)\n'
            '    # Intent に必要な relation 操作と print をここに書く\n```\n\n'
            f'Intent:\n{intent.text}\n\n利用する Dataset ids:\n{datasets}'
        )
        return _parse_candidate(self.llm_client.generate(prompt))
