from .dataset_graph import DatasetGraph
from .hypothesis import Hypothesis
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .question import Question
from .verdict import Verdict
from .services import load_service_graph
from .datasets import load_dataset_graph


class Planner:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def plan(self, question: Question | str) -> list[Hypothesis] | list[Intent]:
        if isinstance(question, str):
            return self.plan_goal(question)
        prompt = (
            "次の疑問に対して、データを使って検証可能な仮説を1つ提案してください。\n"
            "仮説本文だけを返してください。\n\n"
            f"疑問:\n{question.text}"
        )
        return [Hypothesis(self.llm_client.generate(prompt).strip())]

    def plan_intents(
        self, hypothesis: Hypothesis, dataset_graph: DatasetGraph
    ) -> list[Intent]:
        datasets = dataset_graph.all()
        if not datasets:
            raise ValueError("Dataset Graph must not be empty")
        dataset_text = "\n".join(
            f"- {dataset.id}: {dataset.description}" for dataset in datasets
        )
        prompt = (
            "次の仮説を検証するために必要な調査を、具体的な実行単位に分解してください。\n\n"
            "Intent は、1回の Worker 実行で1つの明確な Observation を得るための最小調査単位です。\n"
            "- 1 Intent = 1 measurable output（1つの測定値・集計値だけを得る）\n"
            "- 必要なら複数 Dataset を使ってよい。ただし1 Intent は1 measurable output\n"
            "- spatial join / zonal aggregation / attribute join などの結合・集計を許可する\n"
            "- 複数の異なる測定値を1 Intent にまとめない\n"
            "- 最終的な相関分析や仮説判定は Intent にしない\n"
            "- 測定する指標が複数なら、指標ごとに別の Intent に分ける\n"
            "- 各 Intent は簡易 YAML にし、利用データセットは1件以上の配列にする\n"
            "- 調査項目は1行の文字列、Dataset の id は半角空白2つと - に続けて書く\n"
            "- Intent 同士は、単独行の --- で区切る\n"
            "- Dataset 配列以外の箇条書き、番号、コードフェンス、前置きは付けない\n"
            "- 調査内容だけを書く\n"
            "- 3〜5件程度\n"
            "- 結論は書かない\n"
            "- 利用可能な Dataset の範囲内で Intent を作る\n"
            "- 登録外のデータセットを仮定しない\n"
            "- 各調査で参照する Dataset の id を明記する\n\n"
            "出力形式の例:\n"
            "調査項目: 23区ごとの推計人口を算出する\n"
            "利用データセット:\n"
            "  - yuiseki/jp-admin-2026-09\n"
            "  - yuiseki/worldpop-jp-2026-01\n\n"
            f"利用可能な Dataset:\n{dataset_text}\n\n"
            f"仮説:\n{hypothesis.text}"
        )
        blocks = self.llm_client.generate(prompt).split("---")
        intents = []
        for block in blocks:
            if not block.strip():
                continue
            intent = Intent.from_block(block)
            for dataset_id in intent.dataset_ids:
                dataset_graph.get(dataset_id)
            intents.append(intent)
        if not intents:
            raise ValueError("LLM returned no intents")
        return intents

    def judge(
        self, hypothesis: Hypothesis, observations: list[Observation]
    ) -> Verdict:
        return Verdict("仮説はまだ十分に検証されていない")

    def plan_goal(self, goal: str) -> list[Intent]:
        if not goal.strip():
            raise ValueError('Goal must not be empty')
        datasets, services = load_dataset_graph(), load_service_graph()
        resources = '\n'.join(f'Dataset {item.id}: {item.description}' for item in datasets.all())
        resources += '\n' + '\n'.join(f'Service {item.id}: {item.protocol}: {item.description}' for item in services.all())
        prompt = (
            'Goal を小さい調査 Intent に分解してください。1 Intent = 1 measurable output。\n'
            '依存関係のある順に並べ、取得した情報を後続で使う。巨大なループコードを最初から作らない。\n'
            '後続では previous_observations（前段 stdout の文字列一覧）を参照できる。\n'
            '既に取得した一覧やタグを再検索せず使う。途中の出力は JSON にすると参照しやすい。\n'
            '有限個の対象を比較するとき、対象一覧の取得、任意対象1件の測定、全対象の測定、最大選択を分ける。\n'
            '対象件数が Goal で明示されている場合、全対象の測定は一覧の各番号について同じ小さい Intent を並べてよい。\n'
            '各 Intent は登録済み Dataset 0〜1件または Service 1件以上を指定する。ローカル集計でも由来の Service を指定。\n'
            '答えを推測しない。サービス固有の実行コードを書かない。前段結果に依存する入力を調査項目に明記。\n'
            '出力は以下の3項目のみ。各 Intent を独立行 --- で区切る。前置き、番号、コードフェンス禁止。\n'
            '調査項目: 調査内容\n利用データセット: []\n利用サービス:\n  - 登録済みid\n'
            '利用データセットと利用サービスは空なら []、非空なら半角2空白の - id の行を続ける。\n'
            f'利用可能リソース:\n{resources}\nGoal:\n{goal}'
        )
        text = self.llm_client.generate(prompt, temperature=0.0, max_tokens=4096)
        result = []
        for block in text.strip().split('\n---\n'):
            lines = block.strip().splitlines()
            if not lines or not lines[0].startswith('調査項目: '):
                raise ValueError('Plan must start with 調査項目:')
            ids = {'利用データセット': [], '利用サービス': []}
            position = 1
            for label in ids:
                if position >= len(lines) or lines[position] not in (label + ':', label + ': []'):
                    raise ValueError('Plan must contain dataset and service lists')
                empty = lines[position].endswith(' []')
                position += 1
                if not empty:
                    while position < len(lines) and lines[position].startswith('  - '):
                        ids[label].append(lines[position][4:])
                        position += 1
                    if not ids[label]:
                        raise ValueError('Use [] for empty lists')
            if position != len(lines):
                raise ValueError('Unexpected plan fields')
            intent = Intent(lines[0][len('調査項目: '):], tuple(ids['利用データセット']), tuple(ids['利用サービス']))
            if len(intent.dataset_ids) > 1:
                raise ValueError('Only one dataset per execution is supported')
            for id in intent.dataset_ids:
                datasets.get(id)
            for id in intent.service_ids:
                services.get(id)
            result.append(intent)
        return result
