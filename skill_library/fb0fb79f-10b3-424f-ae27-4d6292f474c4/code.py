from geo_voyager.control_primitives import connect_duckdb, load_stations

with connect_duckdb() as connection:
    stations = load_stations(dataset_id, connection)
    row = stations.order("latitude DESC, name ASC").limit(1).fetchone()
    if row is None:
        raise ValueError("No station found")
    name, latitude, longitude = row
    print(f"駅データに収録されている最北端の駅は{name}駅で、緯度は{latitude}、経度は{longitude}である")
