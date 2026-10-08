from geo_voyager.control_primitives import connect_duckdb, load_admin_units

with connect_duckdb() as connection:
    units = load_admin_units(dataset_id, connection, area="東京都23区")
    rows = units.order("population DESC, code5 ASC").limit(5).fetchall()
    if len(rows) != 5:
        raise ValueError("Five Tokyo wards are required")
    print("東京都23区で人口が多い上位5区:")
    for rank, (_, name, population) in enumerate(rows, start=1):
        if type(population) is not int:
            raise ValueError("Population must be an integer")
        print(f"{rank}位: {name}、人口{population}人")
