"""Write the kinds of things OSM maps in the 23 wards of Tokyo, as tags with their count and description, to
geo_voyager/osm_kinds.tsv.

    .venv/bin/python scripts/sync_osm_kinds.py

Counted on the points and the areas of yuiseki/osm-tokyo23-src-2026-08 at the revision the sandbox reads (the tables
take in what crosses into a ward, so a count is a little more than the wards hold), for the keys below: a value seen
at least MINIMUM times is kept, so that a kind drawn is one the data has. The description is the OSM wiki's, from the
self-hosted taginfo. The curriculum draws a few at random for a Goal of exploration (geo_voyager.ingredients).
"""
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from geo_voyager.dataset_mirror import ensure_mirror, mirror_name  # noqa: E402
from geo_voyager.dataset_tables import TABLE_URLS  # noqa: E402
from geo_voyager.services import HTTP_USER_AGENT  # noqa: E402

PATH = Path(__file__).resolve().parents[1] / 'geo_voyager' / 'osm_kinds.tsv'  # geo_voyager.ingredients reads it
DATASET = 'yuiseki/osm-tokyo23-src-2026-08'
TABLES = ('planet_osm_point', 'planet_osm_polygon')
KEYS = ('amenity', 'leisure', 'shop', 'tourism', 'historic', 'man_made', 'natural', 'sport', 'office', 'landuse',
        'railway', 'aeroway', 'power', 'public_transport', 'waterway', 'place', 'religion', 'military')
MINIMUM = 5
TAGINFO = 'https://taginfo.yuiseki.net/api/4/key/values'


def descriptions(key: str) -> dict[str, str]:
    query = urlencode({'key': key, 'sortname': 'count', 'sortorder': 'desc', 'rp': 999, 'page': 1})
    with urlopen(Request(f'{TAGINFO}?{query}', headers={'User-Agent': HTTP_USER_AGENT}), timeout=60) as response:
        return {row['value']: ' '.join((row.get('description') or '').split()) for row in json.load(response)['data']}


def main() -> None:
    urls = {(DATASET, table): TABLE_URLS[(DATASET, table)] for table in TABLES}
    directory = ensure_mirror(urls=urls)
    paths = [str(directory / mirror_name(url)) for url in urls.values()]
    connection = duckdb.connect()
    lines = []
    for key in KEYS:
        rows = connection.sql(f'SELECT "{key}", count(*) FROM read_parquet(?, union_by_name := true) '
                              f'WHERE "{key}" IS NOT NULL GROUP BY 1 HAVING count(*) >= {MINIMUM} ORDER BY 2 DESC, 1',
                              params=[paths]).fetchall()
        described = descriptions(key)
        for value, count in rows:
            if ';' in value or not value.isascii():
                continue
            lines.append(f'{key}={value}\t{count}\t{described.get(value, "")}')
    PATH.write_text(f'# {DATASET}, points and areas, values seen {MINIMUM} times or more\ntag\tcount\tdescription\n'
                    + '\n'.join(lines) + '\n', encoding='utf-8')
    print(len(lines), 'tags')


if __name__ == '__main__':
    main()
