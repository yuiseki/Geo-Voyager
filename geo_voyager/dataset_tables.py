"""The tables the sandbox can read: every table the dataset references list (dataset_references.json, copied from
GeoAI-master-skills), read at the revision of the dataset's card (ADR 0010).

A reference names a table's file as hf://datasets/<repo>/<path>, or as a Hub URL that may be on a branch
(resolve/main). Both are read at the card's revision here, so a run reads the files the references were measured on
and a later push to the dataset changes nothing until the references are synced again. Standard library only: the
Gateway and the worker image import it.
"""
import json
from pathlib import Path
import re

_DATA = json.loads(Path(__file__).with_name('dataset_references.json').read_text(encoding='utf-8'))
HUB = 'https://huggingface.co/datasets/'


def _pinned(read: str, revision: str) -> str:
    if read.startswith('hf://datasets/'):
        repo_and_path = read.removeprefix('hf://datasets/')
        owner, name, path = repo_and_path.split('/', 2)
        return f'{HUB}{owner}/{name}/resolve/{revision}/{path}'
    match = re.fullmatch(r'(https://huggingface\.co/datasets/[^/]+/[^/]+)/resolve/[^/]+/(.+)', read)
    if not match:
        raise ValueError(f'Not a file on the Hub: {read}')
    return f'{match.group(1)}/resolve/{revision}/{match.group(2)}'


TABLE_URLS = {(dataset_id, table['name']): _pinned(table['read'], reference['card_revision'])
              for dataset_id, reference in _DATA['datasets'].items() for table in reference['tables']}


def table_names(dataset_id: str) -> list[str]:
    return [table for (dataset, table) in TABLE_URLS if dataset == dataset_id]
