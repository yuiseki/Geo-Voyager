"""The Gateway's code goes to `docker run ... python -c` as one argument, which Linux caps at 128 KiB.

With the land prices and the OSM of the 23 wards (2026-10-17), the dataset references grew to 91 KB of mostly
Japanese text, and the Gateway no longer started: OSError: [Errno 7] Argument list too long: 'docker'. The Gateway
needs, of the references, only where each table is read.
"""
import json
from pathlib import Path

from integration.service_gateway_setup import gateway_code

ARGUMENT_LIMIT = 128 * 1024


def test_the_gateways_code_fits_one_argument_of_the_command_line():
    assert len(gateway_code(with_datasets=True, mirror_dir='/mirror').encode('utf-8')) < ARGUMENT_LIMIT * 0.75


def test_the_gateway_is_given_where_every_table_is_read_and_at_which_revision():
    from geo_voyager.dataset_tables import TABLE_URLS, _pinned
    from integration.service_gateway_setup import _where_tables_are_read
    references = (Path(__file__).resolve().parents[1] / 'geo_voyager' / 'dataset_references.json').read_text()
    data = json.loads(_where_tables_are_read(references))
    rebuilt = {(dataset_id, table['name']): _pinned(table['read'], reference['card_revision'])
               for dataset_id, reference in data['datasets'].items() for table in reference['tables']}
    assert rebuilt == TABLE_URLS
