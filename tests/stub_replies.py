"""Replies of a stub model for the tests of the code generation."""


def reply_reading(intent, fallback):
    """A valid reply whose code reads exactly the Datasets the Intent declares, as the contract requires: a table
    with read_table, the population grid with sum_population_grid."""
    from geo_voyager.dataset_tables import TABLE_URLS
    from geo_voyager.skill_candidate import PRIMITIVE_DATASETS
    calls, names = [], set()
    for dataset_id in intent.dataset_ids:
        grid = [name for name, dataset in PRIMITIVE_DATASETS.items() if dataset == dataset_id]
        if grid:
            calls.append(f'        {grid[0]}(connection, None)\n'); names.add(grid[0])
            continue
        table = next((table for (dataset, table), url in TABLE_URLS.items() if dataset == dataset_id and url.endswith('.parquet')), None)
        if table is not None:
            calls.append(f'        read_table(connection, {dataset_id!r}, {table!r})\n'); names.add('read_table')
    if not calls:
        return fallback
    return ('説明:\nS\n---\nコード:\n```python\n'
            f'from geo_voyager.control_primitives import connect_duckdb, {", ".join(sorted(names))}\n\n'
            f'def answer():\n    """Answer."""\n    with connect_duckdb() as connection:\n{"".join(calls)}        return 1\n```')
