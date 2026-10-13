from geo_voyager.dataset_tables import TABLE_URLS, table_names

# The datasets the first primitives read, each from its one file (Dataset.data_url).
_WHOLE = ("yuiseki/jp-admin-2026-09", "yuiseki/ekidata-jp", "yuiseki/worldpop-jp-2026-01")


def dataset_url(dataset_id: str, table: str | None = None) -> str:
    """The Gateway's URL of a dataset's table (any table its reference lists), or of the dataset's one file."""
    if table is not None:
        if (dataset_id, table) not in TABLE_URLS:
            raise ValueError(f"{dataset_id} has no table {table!r}. Its tables: {', '.join(table_names(dataset_id)) or 'none'}")
        return f"http://gateway:8000/datasets/{dataset_id}/{table}"
    if dataset_id not in _WHOLE:
        raise ValueError("Only the administrative, station and population grid datasets are supported")
    return f"http://gateway:8000/datasets/{dataset_id}"
