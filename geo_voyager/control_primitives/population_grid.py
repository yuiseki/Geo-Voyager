import json

from .dataset_url import dataset_url

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'
ADMIN = 'yuiseki/jp-admin-2026-09'
AREAS = {'東京都23区': "code5 BETWEEN '13101' AND '13123'"}


def sum_population_grid(dataset_id: str, connection, *, area: str | None = None):
    """Sum the WorldPop pixels whose centre lies in each administrative unit of area.

    Returns a DuckDB relation (code5, name, estimated_population). The boundaries come from the administrative
    dataset, so the Intent declares only the population grid. A pixel counts for the unit its centre is in, as
    rasterio.mask does by default; the pixels of the boundary are what makes this differ from a census.
    """
    if dataset_id != WORLDPOP:
        raise ValueError('Only the WorldPop population grid is supported')
    if area not in AREAS:
        raise ValueError(f'Unsupported area: {area}')
    import rasterio
    import rasterio.mask

    units = connection.read_parquet(dataset_url(ADMIN)).filter(AREAS[area]).project(
        'code5, name, ST_AsGeoJSON(geometry) AS geojson').order('code5').fetchall()
    url = dataset_url(dataset_id)
    path = '/vsicurl/' + url if url.startswith('http') else url
    sums = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'), rasterio.open(path) as source:
        for code5, name, geojson in units:
            pixels, _ = rasterio.mask.mask(source, [json.loads(geojson)], crop=True, filled=False)
            # WorldPop's missing value is -99999. A rasterio that picks up another GDAL's data files reports no
            # nodata at all, and the missing pixels were summed as people; no population is negative.
            values = pixels[0].compressed() if hasattr(pixels[0], 'compressed') else pixels[0].ravel()
            sums.append((code5, name, float(values[values >= 0].sum())))
    connection.execute('CREATE OR REPLACE TEMP TABLE population_grid_sums '
                       '(code5 VARCHAR, name VARCHAR, estimated_population DOUBLE)')
    connection.executemany('INSERT INTO population_grid_sums VALUES (?, ?, ?)', sums)
    return connection.table('population_grid_sums')
