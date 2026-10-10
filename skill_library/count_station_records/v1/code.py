from geo_voyager.control_primitives import connect_duckdb, load_stations


def count_station_records(dataset_id):
    """Count every record of the station dataset, with no filtering by operating state and no merging of the same station."""
    with connect_duckdb() as connection:
        return load_stations(dataset_id, connection).aggregate("count(*) AS station_count").fetchone()[0]
