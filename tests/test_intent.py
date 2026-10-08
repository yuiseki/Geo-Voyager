import pytest

from geo_voyager.intent import Intent


@pytest.mark.parametrize("text", ["", " "])
def test_intent_rejects_empty_text(text):
    with pytest.raises(ValueError):
        Intent(text, "yuiseki/ekidata-jp")


@pytest.mark.parametrize("dataset_id", ["", " "])
def test_intent_rejects_empty_dataset_id(dataset_id):
    with pytest.raises(ValueError):
        Intent("駅数を集計する", dataset_id)


def test_intent_parses_two_field_block():
    intent = Intent.from_block(
        "調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp"
    )

    assert intent == Intent("駅数を集計する", "yuiseki/ekidata-jp")


@pytest.mark.parametrize(
    "block",
    [
        "利用データセット: yuiseki/ekidata-jp",
        "調査項目: 駅数を集計する",
        "調査項目: \n利用データセット: yuiseki/ekidata-jp",
        "調査項目: 駅数を集計する\n利用データセット: ",
        "調査項目: 駅数を集計する\n利用データセット: yuiseki/ekidata-jp\n追加項目: 不要",
        "調査項目: 駅数を集計する\n調査項目: 別の調査",
    ],
)
def test_intent_rejects_invalid_block(block):
    with pytest.raises(ValueError):
        Intent.from_block(block)
