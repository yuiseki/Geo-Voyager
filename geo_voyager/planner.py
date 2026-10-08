from .dataset_graph import DatasetGraph
from .hypothesis import Hypothesis
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .question import Question
from .verdict import Verdict


class Planner:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def plan(self, question: Question) -> list[Hypothesis]:
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
            "- 1 Intent = 1 primary dataset（原則1つの Dataset を主に使う）\n"
            "- 1 Intent = 1 measurable output（1つの測定値・集計値だけを得る）\n"
            "- 複数 Dataset をまとめた総合分析は Intent にしない\n"
            "- 最終的な相関分析や仮説判定は Intent にしない\n"
            "- 測定する指標が複数なら、指標ごとに別の Intent に分ける\n"
            "- 各 Intent は2行の簡易 YAML にする\n"
            "- 1行目は「調査項目: 調査内容」、2行目は「利用データセット: 登録済み Dataset の id」\n"
            "- コロンは半角で直後に空白を置き、値は1行の文字列にする\n"
            "- Intent 同士は、単独行の --- で区切る\n"
            "- 番号、箇条書き、コードフェンス、前置きは付けない\n"
            "- 調査内容だけを書く\n"
            "- 3〜5件程度\n"
            "- 結論は書かない\n"
            "- 利用可能な Dataset の範囲内で Intent を作る\n"
            "- 登録外のデータセットを仮定しない\n"
            "- 各調査で参照する Dataset の id を明記する\n\n"
            f"利用可能な Dataset:\n{dataset_text}\n\n"
            f"仮説:\n{hypothesis.text}"
        )
        blocks = self.llm_client.generate(prompt).split("---")
        intents = []
        for block in blocks:
            if not block.strip():
                continue
            intent = Intent.from_block(block)
            dataset_graph.get(intent.dataset_id)
            intents.append(intent)
        if not intents:
            raise ValueError("LLM returned no intents")
        return intents

    def judge(
        self, hypothesis: Hypothesis, observations: list[Observation]
    ) -> Verdict:
        return Verdict("仮説はまだ十分に検証されていない")
