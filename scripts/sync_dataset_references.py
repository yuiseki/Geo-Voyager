"""Copy the YAML frontmatter of the dataset references in GeoAI-skills (the How-to Graph) into
geo_voyager/dataset_references.json, at a fixed commit.

    uvx --with pyyaml python scripts/sync_dataset_references.py ../GeoAI-skills <commit>

The references are measured facts about each dataset (what a row is, its ids and join keys, the keys it does not
have, what the main columns mean). GeoAI-skills is where they are kept; this copies the ones of the datasets the
sandbox can read, so that a run does not depend on another checkout and the commit it was made from is recorded.
"""
import json
from pathlib import Path
import subprocess
import sys

import yaml

REFERENCES = {
    'yuiseki/jp-admin-2026-09': 'jp-admin-2026-09.md',
    'yuiseki/ekidata-jp': 'ekidata-jp.md',
    'yuiseki/worldpop-jp-2026-01': 'worldpop/japan.md',
}
DIRECTORY = '.agents/skills/dataset-discovery/references/'
OUT = Path(__file__).resolve().parents[1] / 'geo_voyager' / 'dataset_references.json'


def frontmatter(text: str) -> dict:
    if not text.startswith('---\n'):
        raise ValueError('the reference has no YAML frontmatter')
    return yaml.safe_load(text.split('---\n', 2)[1])


def main() -> None:
    repository, commit = sys.argv[1], sys.argv[2]
    commit = subprocess.run(['git', '-C', repository, 'rev-parse', commit], check=True, capture_output=True, text=True).stdout.strip()
    datasets = {}
    for dataset_id, path in REFERENCES.items():
        text = subprocess.run(['git', '-C', repository, 'show', f'{commit}:{DIRECTORY}{path}'],
                              check=True, capture_output=True, text=True).stdout
        datasets[dataset_id] = frontmatter(text)
        if datasets[dataset_id]['id'] != dataset_id:
            raise ValueError(f'{path} is about {datasets[dataset_id]["id"]}, not {dataset_id}')
    source = {'repository': 'https://github.com/yuiseki/GeoAI-skills', 'commit': commit,
              'paths': {dataset_id: DIRECTORY + path for dataset_id, path in REFERENCES.items()}}
    OUT.write_text(json.dumps({'source': source, 'datasets': datasets}, ensure_ascii=False, indent=1, default=str) + '\n')
    print(OUT, commit)


if __name__ == '__main__':
    main()
