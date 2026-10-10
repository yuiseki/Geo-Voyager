import importlib

import pytest


@pytest.fixture
def primitives(tmp_path, monkeypatch):
    (tmp_path / 'data' / 'michiyomi').mkdir(parents=True)
    (tmp_path / 'data' / 'michiyomi' / 'taito.parquet').write_bytes(b'PAR1')
    (tmp_path / 'out').mkdir()
    monkeypatch.setenv('GEO_VOYAGER_ANALYSIS_DATA_ROOT', str(tmp_path / 'data'))
    monkeypatch.setenv('GEO_VOYAGER_ANALYSIS_OUT_ROOT', str(tmp_path / 'out'))
    import geo_voyager.analysis_primitives.data as data
    return importlib.reload(data), tmp_path


def test_a_data_file_is_found_under_the_data_root(primitives):
    data, root = primitives
    assert data.data_path('michiyomi/taito.parquet') == str(root / 'data' / 'michiyomi' / 'taito.parquet')


def test_a_missing_data_file_names_what_is_there(primitives):
    data, _ = primitives
    with pytest.raises(FileNotFoundError, match='michiyomi/taito.parquet'):
        data.data_path('michiyomi/sumida.parquet')


@pytest.mark.parametrize('name', ['/etc/passwd', '../secret', 'a/../../b', ''])
def test_a_name_outside_the_root_is_refused(primitives, name):
    data, _ = primitives
    with pytest.raises(ValueError):
        data.data_path(name)
    with pytest.raises(ValueError):
        data.output_path(name)


def test_an_output_path_is_under_the_output_root_and_its_folder_is_made(primitives):
    data, root = primitives
    assert data.output_path('maps/pc1.png') == str(root / 'out' / 'maps' / 'pc1.png')
    assert (root / 'out' / 'maps').is_dir()
