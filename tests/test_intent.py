import pytest

from geo_voyager.intent import Intent


@pytest.mark.parametrize("text", ["", " "])
def test_intent_rejects_empty_text(text):
    with pytest.raises(ValueError):
        Intent(text, ("yuiseki/ekidata-jp",))


@pytest.mark.parametrize("dataset_ids", [(), ("",), (" ",)])
def test_intent_rejects_empty_dataset_ids(dataset_ids):
    with pytest.raises(ValueError):
        Intent("駅数を集計する", dataset_ids)


@pytest.mark.parametrize(
    "dataset_ids",
    [("yuiseki/jp-admin-2026-09",), ("yuiseki/jp-admin-2026-09", "yuiseki/worldpop-jp-2026-01")],
)
def test_intent_parses_dataset_list(dataset_ids):
    block = "調査項目: 推計人口を算出する\n利用データセット:\n" + "\n".join(
        f"  - {dataset_id}" for dataset_id in dataset_ids
    )

    assert Intent.from_block(block) == Intent("推計人口を算出する", dataset_ids)


@pytest.mark.parametrize(
    "block",
    [
        "利用データセット:\n  - yuiseki/ekidata-jp",
        "調査項目: 駅数を集計する",
        "調査項目: \n利用データセット:\n  - yuiseki/ekidata-jp",
        "調査項目: 駅数を集計する\n利用データセット: ",
        "調査項目: 駅数を集計する\n利用データセット:\n  - yuiseki/ekidata-jp\n追加項目: 不要",
        "調査項目: 駅数を集計する\n調査項目: 別の調査",
        "調査項目: 駅数を集計する\n利用データセット:\n  - ",
    ],
)
def test_intent_rejects_invalid_block(block):
    with pytest.raises(ValueError):
        Intent.from_block(block)


def test_service_only_intent_needs_no_dummy_dataset():
    intent = Intent('地名を検索する', service_ids=('nominatim',))
    assert intent.dataset_ids == () and intent.service_ids == ('nominatim',)


def test_intent_rejects_empty_service_ids():
    with pytest.raises(ValueError):
        Intent('調査', service_ids=('',))


def test_intent_target_name_is_optional_and_defaults_to_none():
    assert Intent("駅数を集計する", ("yuiseki/ekidata-jp",)).target_name is None
    assert Intent("港区の件数", service_ids=("overpass",), target_name="港区").target_name == "港区"


@pytest.mark.parametrize("name", ["", "  "])
def test_intent_rejects_an_empty_target_name(name):
    with pytest.raises(ValueError):
        Intent("港区の件数", service_ids=("overpass",), target_name=name)
