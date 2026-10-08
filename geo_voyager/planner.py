from .hypothesis import Hypothesis
from .intent import Intent
from .observation import Observation
from .question import Question
from .verdict import Verdict


class Planner:
    def plan(self, question: Question) -> list[Hypothesis]:
        return [Hypothesis("コンビニ密度には区ごとの差がある")]

    def plan_intents(self, hypothesis: Hypothesis) -> list[Intent]:
        return [Intent("東京23区ごとのコンビニ件数を調べる")]

    def judge(
        self, hypothesis: Hypothesis, observations: list[Observation]
    ) -> Verdict:
        return Verdict("仮説はまだ十分に検証されていない")
