from geo_voyager.control_primitives import connect_duckdb, load_stations

with connect_duckdb() as connection:
    stations = load_stations(dataset_id, connection)
    count = stations.aggregate("count(*) AS station_count").fetchone()[0]
    print(f"駅データに収録されている駅の総数は{count}件である（全レコード数、重複排除なし）")
