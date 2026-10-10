from geo_voyager.control_primitives import connect_duckdb, load_admin_units


def total_population(dataset_id, area=None):
    """Sum the population of the administrative areas, all of them or one named set (for example 東京都23区)."""
    with connect_duckdb() as connection:
        total = load_admin_units(dataset_id, connection, area=area).aggregate("sum(population) AS population_total").fetchone()[0]
    if type(total) is not int:
        raise TypeError("The population total must be an integer")
    return total
