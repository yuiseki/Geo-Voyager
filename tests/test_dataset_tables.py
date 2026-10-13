"""The tables the sandbox can read are those the dataset references list (ADR 0010), each read at the dataset's
pinned revision, never at a branch."""
from geo_voyager.dataset_tables import TABLE_URLS, table_names


def test_every_table_of_the_references_is_served():
    assert table_names('yuiseki/jp-admin-2026-09') == ['municipalities', 'prefectures']
    assert table_names('yuiseki/ekidata-jp') == ['station', 'line', 'company', 'join', 'pref']
    assert 'population_100m_2020' in table_names('yuiseki/worldpop-jp-2026-01')


def test_an_hf_path_is_read_at_the_cards_revision():
    assert TABLE_URLS[('yuiseki/ekidata-jp', 'line')] == (
        'https://huggingface.co/datasets/yuiseki/ekidata-jp/resolve/a33321099406b47338be0d03a4887059473fde0c/'
        'parquet/2026-10-05/line.2026-06-18.parquet')


def test_a_url_on_a_branch_is_pinned_to_the_cards_revision_too():
    url = TABLE_URLS[('yuiseki/worldpop-jp-2026-01', 'population_100m_2020')]
    assert '/resolve/cb54e5985662c617a235278bc3529cc172e6368c/cog/' in url and '/resolve/main/' not in url


def test_the_pinned_files_are_the_ones_the_catalog_read_before():
    from geo_voyager.datasets import load_dataset_graph
    graph = load_dataset_graph()
    assert TABLE_URLS[('yuiseki/jp-admin-2026-09', 'municipalities')] == graph.get('yuiseki/jp-admin-2026-09').data_url
    assert TABLE_URLS[('yuiseki/ekidata-jp', 'station')] == graph.get('yuiseki/ekidata-jp').data_url
    assert TABLE_URLS[('yuiseki/worldpop-jp-2026-01', 'population_100m_2020')] == graph.get('yuiseki/worldpop-jp-2026-01').data_url


def test_every_url_is_on_the_hub_and_pinned():
    import re
    for url in TABLE_URLS.values():
        assert re.fullmatch(r'https://huggingface\.co/datasets/yuiseki/[\w.-]+/resolve/[0-9a-f]{40}/\S+', url), url
