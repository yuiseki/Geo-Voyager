from geo_voyager.control_primitives import connect_duckdb, load_admin_units

with connect_duckdb() as connection:
    units = load_admin_units(dataset_id, connection)
    row = units.filter("code5 BETWEEN '13101' AND '13123'").order("population DESC").limit(1).fetchone()
    if row is None:
        raise ValueError("No Tokyo ward found")
    _, name, population = row
    if type(population) is not int:
        raise TypeError("population must be an integer")
    print(f"東京都23区で人口が最も多い区は{name}で、人口は{population}人である")
