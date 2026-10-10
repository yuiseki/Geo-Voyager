from geo_voyager.control_primitives import connect_duckdb, load_admin_units


def least_populous_area(dataset_id, area=None):
    """Find the administrative area with the smallest population, in all areas or in one named set (for example 東京都23区). Returns its 5-digit code, name and population."""
    with connect_duckdb() as connection:
        row = load_admin_units(dataset_id, connection, area=area).order("population ASC, code5 ASC").limit(1).fetchone()
    if row is None:
        raise ValueError("No administrative area found")
    code5, name, population = row
    if type(population) is not int:
        raise TypeError("population must be an integer")
    return {"code5": code5, "name": name, "population": population}
