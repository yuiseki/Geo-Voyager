import pytest
from geo_voyager.datasets import load_dataset_graph


def test_catalog_registers_researched_datasets():
    graph = load_dataset_graph()
    expected = {
        "yuiseki/osm-japan-src-2026-08",
        "yuiseki/mlit-toshi-keikaku-jp",
        "yuiseki/jp-admin-2026-09",
        "yuiseki/ekidata-jp",
        "yuiseki/worldpop-jp-2026-01",
    }

    assert len(graph.all()) >= 5
    assert expected <= {dataset.id for dataset in graph.all()}
    for dataset_id in expected:
        dataset = graph.get(dataset_id)
        assert dataset.url == f"https://huggingface.co/datasets/{dataset_id}"
        assert dataset.description
        assert dataset.contents


def test_admin_dataset_has_one_pinned_municipalities_download_url():
    dataset = load_dataset_graph().get("yuiseki/jp-admin-2026-09")
    assert dataset.data_url == (
        "https://huggingface.co/datasets/yuiseki/jp-admin-2026-09/resolve/"
        "e6c87b1d7095c17422147962185071a986e13135/municipalities.parquet"
    )
    assert dataset.url == "https://huggingface.co/datasets/yuiseki/jp-admin-2026-09"


def test_the_readable_datasets_are_the_ones_with_a_data_url_and_the_ones_the_sandbox_can_open():
    from geo_voyager.control_primitives.dataset_url import dataset_url
    from geo_voyager.datasets import load_readable_dataset_graph
    readable = {dataset.id for dataset in load_readable_dataset_graph().all()}
    assert readable == {dataset.id for dataset in load_dataset_graph().all() if dataset.data_url}
    for dataset in load_dataset_graph().all():
        if dataset.id in readable:
            assert dataset_url(dataset.id)
        else:
            with pytest.raises(ValueError):
                dataset_url(dataset.id)
