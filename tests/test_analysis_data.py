import re

from geo_voyager.analysis_data import FILES


def test_every_file_is_pinned_to_a_revision_and_a_digest():
    for item in FILES:
        assert re.search(r'/resolve/[0-9a-f]{40}/', item.url), item.url
        assert re.fullmatch(r'[0-9a-f]{64}', item.sha256) and item.size > 0 and item.license


def test_paths_are_relative_and_distinct():
    paths = [item.path for item in FILES]
    assert len(set(paths)) == len(paths)
    assert all(not path.startswith('/') and '..' not in path.split('/') for path in paths)
