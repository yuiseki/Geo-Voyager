"""Write the kinds of things OSM maps in the 23 wards of Tokyo, as tags with their count, how many of them are areas, and description, to
geo_voyager/osm_kinds.tsv, and how many each ward has to geo_voyager/osm_kinds_by_ward.tsv.

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
BY_WARD = PATH.with_name('osm_kinds_by_ward.tsv')
DATASET = 'yuiseki/osm-tokyo23-src-2026-08'
WARDS = ('yuiseki/jp-admin-2026-09', 'municipalities')
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
    urls[WARDS] = TABLE_URLS[WARDS]
    directory = ensure_mirror(urls=urls)
    paths = [str(directory / mirror_name(urls[(DATASET, table)])) for table in TABLES]
    connection = duckdb.connect()
    connection.sql('LOAD spatial')
    # A point, or a point on the surface of an area, in the ward's boundary: two wards asked of a kind of 6 in all
    # the 23 wards had none (explore 29), as had two of 28 (explore 28).
    connection.sql(f"""CREATE TABLE wards AS SELECT name AS ward, ST_SetCRS(geometry, 'OGC:CRS84') AS geometry
                       FROM read_parquet('{directory / mirror_name(urls[WARDS])}') WHERE code5 BETWEEN '13101' AND '13123'""")
    connection.sql(f"""CREATE TABLE things AS SELECT filename = '{paths[1]}' AS area, * EXCLUDE (way, filename),
                       ST_SetCRS(ST_Transform(CASE WHEN filename = '{paths[1]}' THEN ST_PointOnSurface(way) ELSE way END,
                                              'EPSG:3857', 'OGC:CRS84', always_xy := true), 'OGC:CRS84') AS point
                       FROM read_parquet({paths}, union_by_name := true, filename := true)""")
    connection.sql('CREATE TABLE placed AS SELECT things.* EXCLUDE (point), ward FROM things JOIN wards ON ST_Within(point, geometry)')
    lines = []
    by_ward = []
    for key in KEYS:
        # The areas apart: a Goal on the area of a kind found none where the kind was mapped as points (explore 24).
        rows = connection.sql(f'SELECT "{key}", count(*), count(*) FILTER (WHERE filename = ?) '
                              f'FROM read_parquet(?, union_by_name := true, filename := true) '
                              f'WHERE "{key}" IS NOT NULL GROUP BY 1 HAVING count(*) >= {MINIMUM} ORDER BY 2 DESC, 1',
                              params=[paths[1], paths]).fetchall()
        described = descriptions(key)
        for value, count, areas in rows:
            if ';' in value or not value.isascii():
                continue
            lines.append(f'{key}={value}\t{count}\t{areas}\t{described.get(value, "")}')
            for ward, in_ward, areas_in_ward in connection.sql(
                    f'SELECT ward, count(*), count(*) FILTER (WHERE area) FROM placed WHERE "{key}" = ? GROUP BY 1 ORDER BY 1',
                    params=[value]).fetchall():
                by_ward.append(f'{key}={value}\t{ward}\t{in_ward}\t{areas_in_ward}')
    PATH.write_text(f'# {DATASET}, points and areas, values seen {MINIMUM} times or more\ntag\tcount\tareas\tdescription\n'
                    + '\n'.join(lines) + '\n', encoding='utf-8')
    BY_WARD.write_text(f'# {DATASET}, points and areas in each ward, the kinds of osm_kinds.tsv\ntag\tward\tcount\tareas\n'
                       + '\n'.join(by_ward) + '\n', encoding='utf-8')
    print(len(lines), 'tags', len(by_ward), 'tags in wards')


if __name__ == '__main__':
    main()
