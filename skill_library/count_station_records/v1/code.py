from geo_voyager.control_primitives import connect_duckdb, read_table


def count_station_records():
    """Count every record of the station table, with no filtering by operating state and no merging of the same station (a station on several lines is one record per line)."""
    with connect_duckdb() as connection:
        return read_table(connection, "yuiseki/ekidata-jp", "station").aggregate("count(*) AS station_count").fetchone()[0]
