from geo_voyager.control_primitives import connect_duckdb, load_admin_units

with connect_duckdb() as connection:
    units = load_admin_units(dataset_id, connection, area="東京都23区")
    total = units.aggregate("sum(population) AS population_total").fetchone()[0]
    if type(total) is not int:
        raise ValueError("Population total must be an integer")
    print(f"東京都23区の人口合計は{total}人である")
