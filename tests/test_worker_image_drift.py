"""A benchmark refuses to run on a worker image older than the repository's code.

The control primitives run inside the worker image, copied in when it was built. The sandbox limits were relaxed
(DuckDB 512 MB) and two datasets were added in the repository, but the image was not built again: a whole run of
four Goals ran on the old primitives (DuckDB 64 MB), and their out-of-memory failures looked like the model's.
"""
import hashlib

from bench.infra import image_drift


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def repository(tmp_path):
    (tmp_path / 'geo_voyager' / 'control_primitives').mkdir(parents=True)
    (tmp_path / 'geo_voyager' / 'control_primitives' / 'connect_duckdb.py').write_text('memory_limit = "512MB"\n')
    (tmp_path / 'geo_voyager' / 'services.py').write_text('SERVICES = ()\n')
    return tmp_path


def test_an_image_whose_files_are_the_repositorys_has_no_drift(tmp_path):
    root = repository(tmp_path)
    in_image = {'control_primitives/connect_duckdb.py': digest('memory_limit = "512MB"\n'),
                'services.py': digest('SERVICES = ()\n')}
    assert image_drift(in_image, root) == []


def test_a_file_changed_in_the_repository_since_the_build_is_named(tmp_path):
    root = repository(tmp_path)
    in_image = {'control_primitives/connect_duckdb.py': digest('memory_limit = "64MB"\n'),
                'services.py': digest('SERVICES = ()\n')}
    assert image_drift(in_image, root) == ['control_primitives/connect_duckdb.py']


def test_a_primitive_added_to_the_repository_after_the_build_is_named(tmp_path):
    root = repository(tmp_path)
    (root / 'geo_voyager' / 'control_primitives' / 'dataset_url.py').write_text('WHOLE = ()\n')
    in_image = {'control_primitives/connect_duckdb.py': digest('memory_limit = "512MB"\n'),
                'services.py': digest('SERVICES = ()\n')}
    assert image_drift(in_image, root) == ['control_primitives/dataset_url.py']


def test_a_file_in_the_image_that_the_repository_no_longer_has_is_named(tmp_path):
    root = repository(tmp_path)
    in_image = {'control_primitives/connect_duckdb.py': digest('memory_limit = "512MB"\n'),
                'services.py': digest('SERVICES = ()\n'), 'control_primitives/old.py': digest('x = 1\n')}
    assert image_drift(in_image, root) == ['control_primitives/old.py']
