from geo_voyager.control_primitives import connect_duckdb, read_table


def most_populous_area(where=None):
    """Find the administrative area with the largest population, in all municipalities or in those a condition on the boundaries' columns selects (for example "pref_code = '13' AND name LIKE '%区'" for the 23 wards of Tokyo). Returns its 5-digit code, name and population."""
    with connect_duckdb() as connection:
        units = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities")
        if where is not None:
            units = units.filter(where)
        row = units.project("code5, name, population").order("population DESC, code5 ASC").limit(1).fetchone()
    if row is None:
        raise ValueError("No administrative area found")
    code5, name, population = row
    if type(population) is not int:
        raise TypeError("population must be an integer")
    return {"code5": code5, "name": name, "population": population}
