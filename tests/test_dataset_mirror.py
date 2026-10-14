import io
from unittest.mock import MagicMock, patch

import pytest

from geo_voyager.dataset_mirror import ensure_mirror
from geo_voyager.fetch_gateway import mirror_name

URLS = {('a/set', 'rows'): 'https://huggingface.co/datasets/a/set/resolve/abc/rows.parquet'}


def response(body: bytes, length: int | None = None):
    stream = io.BytesIO(body)
    fake = MagicMock()
    fake.read.side_effect = stream.read
    fake.headers = {'Content-Length': str(len(body) if length is None else length)}
    fake.__enter__.return_value = fake
    return fake


def test_a_missing_table_is_copied_once(tmp_path):
    with patch('geo_voyager.dataset_mirror.urlopen', return_value=response(b'parquet')) as urlopen:
        ensure_mirror(tmp_path, URLS)
        ensure_mirror(tmp_path, URLS)
    assert (tmp_path / mirror_name(URLS[('a/set', 'rows')])).read_bytes() == b'parquet'
    assert urlopen.call_count == 1
    assert urlopen.call_args.args[0].get_header('User-agent').startswith('Geo-Voyager/')


def test_a_cut_download_leaves_no_copy(tmp_path):
    with patch('geo_voyager.dataset_mirror.urlopen', return_value=response(b'parq', length=7)):
        with pytest.raises(OSError):
            ensure_mirror(tmp_path, URLS)
    assert list(tmp_path.iterdir()) == [] or all(path.name.endswith('.partial') for path in tmp_path.iterdir())
    assert not (tmp_path / mirror_name(URLS[('a/set', 'rows')])).exists()
