from unittest.mock import Mock

import pytest

from geo_voyager.hypothesis import Hypothesis
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.planner import Planner
from geo_voyager.question import Question
from geo_voyager.verdict import Verdict


def test_planner_returns_hypotheses_for_question():
    question = Question("東京23区でコンビニの分布はどうなっている？")

    client = Mock()
    client.generate.return_value = "  コンビニ密度には区ごとの差がある\n"

    hypotheses = Planner(client).plan(question)

    assert question.text == "東京23区でコンビニの分布はどうなっている？"
    assert isinstance(hypotheses, list)
    assert len(hypotheses) >= 1
    assert all(isinstance(hypothesis, Hypothesis) for hypothesis in hypotheses)
    assert hypotheses == [Hypothesis("コンビニ密度には区ごとの差がある")]
    client.generate.assert_called_once()
    assert question.text in client.generate.call_args.args[0]


def test_planner_returns_intents_for_hypothesis():
    hypothesis = Hypothesis("コンビニ密度には区ごとの差がある")

    intents = Planner().plan_intents(hypothesis)

    assert isinstance(intents, list)
    assert len(intents) >= 1
    assert all(isinstance(intent, Intent) for intent in intents)
    assert all(intent.text for intent in intents)


def test_planner_returns_verdict_for_hypothesis_and_observations():
    hypothesis = Hypothesis("コンビニ密度には区ごとの差がある")
    observations = [Observation("調査対象は東京23区である")]

    verdict = Planner().judge(hypothesis, observations)

    assert isinstance(verdict, Verdict)
    assert verdict.text


@pytest.mark.parametrize("response", ["", " \n "])
def test_planner_rejects_empty_llm_response(response):
    client = Mock()
    client.generate.return_value = response

    with pytest.raises(ValueError):
        Planner(client).plan(Question("東京23区でコンビニの分布はどうなっている？"))
