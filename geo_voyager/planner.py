from .hypothesis import Hypothesis
from .intent import Intent
from .question import Question


class Planner:
    def plan(self, question: Question) -> list[Hypothesis]:
        return [Hypothesis("コンビニ密度には区ごとの差がある")]

    def plan_intents(self, hypothesis: Hypothesis) -> list[Intent]:
        return [Intent("東京23区ごとのコンビニ件数を調べる")]
