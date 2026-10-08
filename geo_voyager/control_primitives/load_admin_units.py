from .dataset_url import dataset_url


def load_admin_units(dataset_id: str, connection):
    return connection.read_parquet(dataset_url(dataset_id)).project("code5, name, population")
