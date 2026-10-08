from geo_voyager.hypothesis import Hypothesis
from geo_voyager.intent import Intent
from geo_voyager.planner import Planner
from geo_voyager.question import Question


def test_planner_returns_hypotheses_for_question():
    question = Question("東京23区でコンビニの分布はどうなっている？")

    hypotheses = Planner().plan(question)

    assert question.text == "東京23区でコンビニの分布はどうなっている？"
    assert isinstance(hypotheses, list)
    assert len(hypotheses) >= 1
    assert all(isinstance(hypothesis, Hypothesis) for hypothesis in hypotheses)
    assert all(hypothesis.text for hypothesis in hypotheses)


def test_planner_returns_intents_for_hypothesis():
    hypothesis = Hypothesis("コンビニ密度には区ごとの差がある")

    intents = Planner().plan_intents(hypothesis)

    assert isinstance(intents, list)
    assert len(intents) >= 1
    assert all(isinstance(intent, Intent) for intent in intents)
    assert all(intent.text for intent in intents)
