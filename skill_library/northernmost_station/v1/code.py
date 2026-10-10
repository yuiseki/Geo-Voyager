from geo_voyager.control_primitives import connect_duckdb, load_stations


def northernmost_station(dataset_id):
    """Find the station with the largest latitude in the station dataset, with no filtering by operating state. Returns its name, latitude and longitude."""
    with connect_duckdb() as connection:
        row = load_stations(dataset_id, connection).order("latitude DESC, name ASC").limit(1).fetchone()
    if row is None:
        raise ValueError("No station found")
    name, latitude, longitude = row
    return {"name": name, "latitude": latitude, "longitude": longitude}
