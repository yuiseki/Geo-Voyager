from geo_voyager.control_primitives import connect_duckdb, read_table


def northernmost_station():
    """Find the station with the largest latitude in the station table, with no filtering by operating state. Returns its name, latitude and longitude."""
    with connect_duckdb() as connection:
        row = read_table(connection, "yuiseki/ekidata-jp", "station").project("station_name, lat, lon").order("lat DESC, station_name ASC").limit(1).fetchone()
    if row is None:
        raise ValueError("No station found")
    name, latitude, longitude = row
    return {"name": name, "latitude": latitude, "longitude": longitude}
