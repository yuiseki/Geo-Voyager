import json
from pathlib import Path
from urllib.request import urlopen

from .dataset_arguments import dataset_arguments


def rasterio_mask(source, shapes, **kwargs):
    import rasterio.mask
    return rasterio.mask.mask(source, shapes, **kwargs)


def _parts(geojson: dict) -> list[dict]:
    """A multipolygon's polygons, each cut from the grid on its own window. Cut whole, a municipality of islands far
    apart (Ogasawara, some 17 by 7 degrees) was one window of hundreds of megabytes; the parts do not overlap, so the
    sum is the same."""
    if geojson['type'] == 'MultiPolygon':
        return [{'type': 'Polygon', 'coordinates': polygon} for polygon in geojson['coordinates']]
    return [geojson]
from .dataset_url import dataset_url

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'
# Read by Range through the Gateway, a zone took 0.17 s (1,000 circles of 1 km in 166 s). The 131 MB file is fetched
# whole to the sandbox's /tmp once (17 s) and read there: the 8,766 stations' circles took 6.8 s (2026-10-15).
LOCAL_GRID = Path('/tmp/worldpop-jp-2020-100m.tif')
# The operating stations of Japan (9,281 rows, 8,766 groups), one zone a station.
MAX_ZONES = 20000
# Zones are taken from the relation this many at a time: the faces of the 1,741 municipalities as GeoJSON at once,
# beside the grid and DuckDB, went over the sandbox's 1 GB.
BATCH = 256


def local_grid(url: str) -> Path:
    """The grid at url, fetched once to the sandbox's /tmp."""
    if not LOCAL_GRID.exists():
        partial = LOCAL_GRID.with_name(LOCAL_GRID.name + '.partial')
        with urlopen(url, timeout=120) as response, partial.open('wb') as out:
            while block := response.read(1 << 20):
                out.write(block)
        partial.rename(LOCAL_GRID)
    return LOCAL_GRID


def sum_population_grid(*args):
    """Sum the WorldPop pixels whose centre lies in each zone of a relation with a geometry (OGC:CRS84).

    Returns a DuckDB relation of the zone's other columns and estimated_population. A pixel counts for the zone its
    centre is in, as rasterio.mask does by default; the boundary pixels are why a sum differs from a census.
    """
    connection, zones = dataset_arguments(args, WORLDPOP, 2)
    if 'geometry' not in zones.columns:
        raise ValueError('The zones must have a geometry column (for example the municipalities of read_table)')
    import rasterio

    keys = [column for column in zones.columns if column != 'geometry']
    types = dict(zip(zones.columns, zones.types))
    count = zones.aggregate('count(*)').fetchone()[0]
    if count > MAX_ZONES:
        raise ValueError(f'{count} zones: at most {MAX_ZONES} can be summed at once. Sum them in parts, or make fewer zones')
    url = dataset_url(WORLDPOP)
    path = str(local_grid(url)) if url.startswith('http') else url
    sums = []
    cursor = zones.project(', '.join([f'"{key}"' for key in keys] + ['ST_AsGeoJSON(geometry) AS __geojson']))
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'), rasterio.open(path) as source:
        while batch := cursor.fetchmany(BATCH):
            for *values, geojson in batch:
                total, overlapped = 0.0, False
                for part in _parts(json.loads(geojson)):
                    try:
                        pixels, _ = rasterio_mask(source, [part], crop=True, filled=False)
                    except ValueError:
                        continue                                  # a part outside the grid: no one there
                    overlapped = True
                    # WorldPop's missing value is -99999. A rasterio that picks up another GDAL's data files reports
                    # no nodata at all, and the missing pixels were summed as people; no population is negative.
                    cells = pixels[0].compressed() if hasattr(pixels[0], 'compressed') else pixels[0].ravel()
                    total += float(cells[cells >= 0].sum())
                if not overlapped:
                    raise ValueError(f'A zone lies outside the grid: {values}')
                sums.append((*values, total))
    columns = ''.join(f'"{key}" {types[key]}, ' for key in keys)
    connection.execute(f'CREATE OR REPLACE TEMP TABLE population_grid_sums ({columns}estimated_population DOUBLE)')
    connection.executemany(f'INSERT INTO population_grid_sums VALUES ({", ".join("?" * (len(keys) + 1))})', sums)
    return connection.table('population_grid_sums')
