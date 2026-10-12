from .dataset_arguments import dataset_arguments
from .dataset_url import dataset_url

STATIONS = 'yuiseki/ekidata-jp'
# One record per station and line: a station on two lines is two records with one station_g_cd.
# status is ekidata's e_status: 0 in service, 1 not yet open, 2 closed. The geometry is the file's, in OGC:CRS84.
COLUMNS = ('station_cd, station_g_cd, line_cd, station_name AS name, e_status AS status, '
           'lat AS latitude, lon AS longitude, geometry')


def load_stations(*args):
    """The station records as a DuckDB relation (station_cd, station_g_cd, line_cd, name, status, latitude,
    longitude, geometry)."""
    (connection,) = dataset_arguments(args, STATIONS, 1)
    return connection.read_parquet(dataset_url(STATIONS)).project(COLUMNS)
