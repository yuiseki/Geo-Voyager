import json

from .dataset_arguments import dataset_arguments
from .dataset_url import dataset_url

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'
# Each zone is a window read by Range through the Gateway. All of Japan is the whole 131 MB file, which the
# sandbox's time limit does not allow; the 23 wards read in about 30 seconds.
MAX_ZONES = 100


def sum_population_grid(*args):
    """Sum the WorldPop pixels whose centre lies in each zone of a relation with a geometry (OGC:CRS84).

    Returns a DuckDB relation of the zone's other columns and estimated_population. A pixel counts for the zone its
    centre is in, as rasterio.mask does by default; the boundary pixels are why a sum differs from a census.
    """
    connection, zones = dataset_arguments(args, WORLDPOP, 2)
    if 'geometry' not in zones.columns:
        raise ValueError('The zones must have a geometry column (for example load_admin_units(connection))')
    import rasterio
    import rasterio.mask

    keys = [column for column in zones.columns if column != 'geometry']
    types = dict(zip(zones.columns, zones.types))
    rows = zones.project(', '.join([f'"{key}"' for key in keys] + ['ST_AsGeoJSON(geometry) AS __geojson'])).fetchall()
    if len(rows) > MAX_ZONES:
        raise ValueError(f'{len(rows)} zones: at most {MAX_ZONES} can be summed at once')
    url = dataset_url(WORLDPOP)
    path = '/vsicurl/' + url if url.startswith('http') else url
    sums = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'), rasterio.open(path) as source:
        for *values, geojson in rows:
            pixels, _ = rasterio.mask.mask(source, [json.loads(geojson)], crop=True, filled=False)
            # WorldPop's missing value is -99999. A rasterio that picks up another GDAL's data files reports no
            # nodata at all, and the missing pixels were summed as people; no population is negative.
            cells = pixels[0].compressed() if hasattr(pixels[0], 'compressed') else pixels[0].ravel()
            sums.append((*values, float(cells[cells >= 0].sum())))
    columns = ', '.join(f'"{key}" {types[key]}' for key in keys)
    connection.execute(f'CREATE OR REPLACE TEMP TABLE population_grid_sums ({columns}, estimated_population DOUBLE)')
    connection.executemany(f'INSERT INTO population_grid_sums VALUES ({", ".join("?" * (len(keys) + 1))})', sums)
    return connection.table('population_grid_sums')
