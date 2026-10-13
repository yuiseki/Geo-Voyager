"""How a Parquet file is laid out, measured from its footer: the columns it is split by.

A column that holds one value in each row group, and different values across them, is what the file was written
in pieces of. A condition on it lets DuckDB skip the other row groups; a condition only on other columns reads them
all. Measured at sync time (scripts/sync_dataset_references.py) and shown in the table contract."""


def split_columns(connection, url: str) -> tuple[int, list[str]]:
    """The number of row groups and, if there are several, the columns with one value in each and not one value
    in all, in the file's column order."""
    rows = connection.execute(
        "SELECT path_in_schema, row_group_id, stats_min_value, stats_max_value, column_id "
        f"FROM parquet_metadata('{url}')").fetchall()
    groups = len({row[1] for row in rows})
    if groups < 2:
        return groups, []
    columns: dict[str, tuple[int, list]] = {}
    for name, _, low, high, column_id in rows:
        columns.setdefault(name, (column_id, []))[1].append((low, high))
    split = [name for name, (_, ranges) in sorted(columns.items(), key=lambda item: item[1][0])
             if all(low is not None and low == high for low, high in ranges) and len({low for low, _ in ranges}) > 1]
    return groups, split
