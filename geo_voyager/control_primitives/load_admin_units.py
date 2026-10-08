from .dataset_url import dataset_url


def load_admin_units(dataset_id: str, connection, *, area: str | None = None):
    if dataset_id != 'yuiseki/jp-admin-2026-09':
        raise ValueError('Only the administrative dataset is supported')
    if area not in (None, '東京都23区'):
        raise ValueError(f'Unsupported area: {area}')
    units = connection.read_parquet(dataset_url(dataset_id)).project('code5, name, population')
    if area == '東京都23区':
        return units.filter("code5 BETWEEN '13101' AND '13123'")
    return units
