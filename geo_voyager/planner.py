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

    def plan_intents(self, hypothesis: Hypothesis) -> list[Intent]:
        return [Intent("東京23区ごとのコンビニ件数を調べる")]

    def judge(
        self, hypothesis: Hypothesis, observations: list[Observation]
    ) -> Verdict:
        return Verdict("仮説はまだ十分に検証されていない")
