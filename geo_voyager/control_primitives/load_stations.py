from .dataset_url import dataset_url


def load_stations(dataset_id: str, connection):
    if dataset_id != 'yuiseki/ekidata-jp':
        raise ValueError('Only the station dataset is supported')
    return connection.read_parquet(dataset_url(dataset_id)).project(
        'station_name AS name, lat AS latitude, lon AS longitude'
    )
