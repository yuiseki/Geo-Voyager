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
