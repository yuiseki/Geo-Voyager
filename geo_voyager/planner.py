from .hypothesis import Hypothesis
from .question import Question


class Planner:
    def plan(self, question: Question) -> list[Hypothesis]:
        return [Hypothesis("コンビニ密度には区ごとの差がある")]
