"""Local copies of the tables the Gateway serves, so a range read does not go to the Hub's CDN each time.

Each table URL names a revision (geo_voyager.dataset_tables), so a copy is made once and never goes stale. The
Gateway reads a copy when there is one (geo_voyager.fetch_gateway) and goes to the Hub otherwise.
"""
import os
from pathlib import Path
from urllib.request import Request, urlopen

from geo_voyager.dataset_tables import TABLE_URLS
from geo_voyager.fetch_gateway import mirror_name
from geo_voyager.services import HTTP_USER_AGENT

DEFAULT_DIR = Path(os.environ.get('GEO_VOYAGER_MIRROR_DIR', Path(__file__).resolve().parents[1] / '.cache' / 'datasets'))


def ensure_mirror(directory: Path = DEFAULT_DIR, urls: dict = TABLE_URLS) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for url in urls.values():
        target = directory / mirror_name(url)
        if target.exists():
            continue
        partial = target.with_name(target.name + '.partial')
        with urlopen(Request(url, headers={'User-Agent': HTTP_USER_AGENT}), timeout=60) as response, partial.open('wb') as out:
            expected = int(response.headers['Content-Length'])
            while block := response.read(1 << 20):
                out.write(block)
        if partial.stat().st_size != expected:
            raise OSError(f'{url}: got {partial.stat().st_size} of {expected} bytes')
        partial.rename(target)
    return directory
