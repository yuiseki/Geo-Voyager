from geo_voyager.control_primitives import connect_duckdb, read_table


def total_population(where=None):
    """Sum the 2020 census population of the administrative areas, in all municipalities or in those a condition on the boundaries' columns selects (for example "pref_code = '13' AND name LIKE '%区'" for the 23 wards of Tokyo). A designated city and its wards are both rows: a national total takes "ward IS NULL"."""
    with connect_duckdb() as connection:
        units = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities")
        if where is not None:
            units = units.filter(where)
        total = units.aggregate("sum(population) AS population_total").fetchone()[0]
    if type(total) is not int:
        raise TypeError("The population total must be an integer")
    return total
