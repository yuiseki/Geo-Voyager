from geo_voyager.control_primitives import connect_duckdb, load_admin_units


def top_areas_by_population(dataset_id, count, area=None):
    """List the given number of administrative areas with the largest populations, largest first, in all areas or in one named set (for example 東京都23区). Each item has its 5-digit code, name and population."""
    with connect_duckdb() as connection:
        rows = load_admin_units(dataset_id, connection, area=area).order("population DESC, code5 ASC").limit(count).fetchall()
    if len(rows) != count:
        raise ValueError(f"{count} areas are required, {len(rows)} found")
    if any(type(population) is not int for _, _, population in rows):
        raise TypeError("population must be an integer")
    return [{"code5": code5, "name": name, "population": population} for code5, name, population in rows]
