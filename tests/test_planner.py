from unittest.mock import Mock

import pytest

from geo_voyager.dataset_graph import DatasetGraph
from geo_voyager.datasets import load_dataset_graph
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


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            "  調査項目: 人口密度を算出する\n利用データセット: yuiseki/jp-admin-2026-09\n",
            ["調査項目: 人口密度を算出する\n利用データセット: yuiseki/jp-admin-2026-09"],
        ),
        (
            "調査項目: 人口密度を算出する\n利用データセット: yuiseki/jp-admin-2026-09"
            "\n---\n調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp",
            [
                "調査項目: 人口密度を算出する\n利用データセット: yuiseki/jp-admin-2026-09",
                "調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp",
            ],
        ),
        (
            "\n---\n \n---\n調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp\n---\n",
            ["調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp"],
        ),
    ],
)

def test_planner_returns_intents_for_hypothesis(response, expected):
    hypothesis = Hypothesis("コンビニ密度には区ごとの差がある")
    client = Mock()
    client.generate.return_value = response

    intents = Planner(client).plan_intents(hypothesis, load_dataset_graph())

    assert isinstance(intents, list)
    assert intents == [Intent(text) for text in expected]
    client.generate.assert_called_once()
    assert hypothesis.text in client.generate.call_args.args[0]


@pytest.mark.parametrize("response", ["", " \n\t\n ", "---\n \n---"])
def test_planner_rejects_empty_intent_response(response):
    client = Mock()
    client.generate.return_value = response

    with pytest.raises(ValueError):
        Planner(client).plan_intents(
            Hypothesis("コンビニ密度には区ごとの差がある"), load_dataset_graph()
        )


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


def test_intent_prompt_includes_registered_dataset_metadata():
    client = Mock()
    client.generate.return_value = "登録済みデータのコンビニ件数を調べる"
    graph = load_dataset_graph()

    intents = Planner(client).plan_intents(Hypothesis("コンビニ密度には差がある"), graph)

    assert intents == [Intent("登録済みデータのコンビニ件数を調べる")]
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    for dataset in graph.all():
        assert dataset.id in prompt
        assert dataset.description in prompt
    assert "利用可能な Dataset の範囲内" in prompt
    assert "登録外のデータセットを仮定しない" in prompt


def test_planner_rejects_empty_dataset_graph_before_calling_llm():
    client = Mock()

    with pytest.raises(ValueError, match="Dataset Graph"):
        Planner(client).plan_intents(Hypothesis("コンビニ密度には差がある"), DatasetGraph())

    client.generate.assert_not_called()


@pytest.mark.parametrize(
    "rule",
    ["1 Intent = 1 primary dataset", "1 Intent = 1 measurable output"],
)
def test_intent_prompt_requires_minimal_investigation_unit(rule):
    client = Mock()
    client.generate.return_value = "yuiseki/ekidata-jp から鉄道駅数を集計する"

    Planner(client).plan_intents(
        Hypothesis("コンビニ密度には区ごとの差がある"), load_dataset_graph()
    )

    client.generate.assert_called_once()
    assert rule in client.generate.call_args.args[0]


def test_intent_prompt_requests_yaml_blocks_separated_by_delimiter():
    client = Mock()
    client.generate.return_value = "調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp"

    Planner(client).plan_intents(Hypothesis("コンビニ密度には差がある"), load_dataset_graph())

    prompt = client.generate.call_args.args[0]
    assert "簡易 YAML" in prompt
    assert "調査項目:" in prompt
    assert "利用データセット:" in prompt
    assert "---" in prompt
    assert "1行につき1 Intent" not in prompt
