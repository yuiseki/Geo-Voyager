from .dataset_arguments import dataset_arguments
from .dataset_url import dataset_url

ADMIN = 'yuiseki/jp-admin-2026-09'
AREAS = {'東京都23区': "code5 BETWEEN '13101' AND '13123'"}
# The boundaries are labelled JGD2000 (EPSG:4612). In Japan JGD2000 and WGS84 agree to about a metre, so the
# label is changed to OGC:CRS84 without a transformation; DuckDB refuses to compare geometries whose labels differ,
# and the stations and the population grid are in CRS84.
COLUMNS = "code5, name, population, ST_SetCRS(geometry, 'OGC:CRS84') AS geometry"


def load_admin_units(*args, area: str | None = None):
    """The municipalities as a DuckDB relation (code5, name, population, geometry), all of them or one area."""
    (connection,) = dataset_arguments(args, ADMIN, 1)
    if area is not None and area not in AREAS:
        raise ValueError(f'Unsupported area: {area}')
    units = connection.read_parquet(dataset_url(ADMIN)).project(COLUMNS)
    return units.filter(AREAS[area]) if area is not None else units
