from geo_voyager.control_primitives import connect_duckdb, read_table


def top_areas_by_population(count, where=None):
    """List the given number of administrative areas with the largest populations, largest first, in all municipalities or in those a condition on the boundaries' columns selects (for example "pref_code = '13' AND name LIKE '%区'" for the 23 wards of Tokyo). Each item has its 5-digit code, name and population."""
    with connect_duckdb() as connection:
        units = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities")
        if where is not None:
            units = units.filter(where)
        rows = units.project("code5, name, population").order("population DESC, code5 ASC").limit(count).fetchall()
    if len(rows) != count:
        raise ValueError(f"{count} areas are required, {len(rows)} found")
    if any(type(population) is not int for _, _, population in rows):
        raise TypeError("population must be an integer")
    return [{"code5": code5, "name": name, "population": population} for code5, name, population in rows]
