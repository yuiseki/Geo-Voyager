from geo_voyager.dataset_tables import TABLE_URLS, table_names

from .dataset_url import dataset_url

# Longitude and latitude on the GRS80/WGS 84 ellipsoids. jp-admin is labelled JGD2000 (EPSG:4612), ekidata OGC:CRS84;
# DuckDB refuses a spatial join between two labels, and the two differ by less than a station's position is precise
# (GeoAI-master-skills, dataset-discovery/references/jp-admin-2026-09.md).
LONGITUDE_LATITUDE = ("EPSG:4612", "EPSG:4326", "OGC:CRS84")
# osm2pgsql's tables are in Web Mercator metres, where areas and distances are larger than on the ground (by 1.52 in
# area at Tokyo). They are turned to longitude and latitude, so they join the other tables and are measured alike.
WEB_MERCATOR = "EPSG:3857"


def read_table(connection, dataset_id, table):
    """Every column of a table a dataset's reference lists (its rows, ids, keys and columns are in the reference), as
    a DuckDB relation under the reference's column names. A longitude/latitude geometry is labelled OGC:CRS84, and a
    Web Mercator one (OpenStreetMap's way) is turned to it, so the tables of two datasets join in space. An area is a condition on the columns, for example
    read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities").filter("pref_code = '13' AND name LIKE '%区'")
    for the 23 wards of Tokyo."""
    if (dataset_id, table) not in TABLE_URLS:
        raise ValueError(f"{dataset_id} has no table {table!r}. Its tables: {', '.join(table_names(dataset_id)) or 'none'}")
    if not TABLE_URLS[(dataset_id, table)].endswith(".parquet"):
        raise ValueError(f"{dataset_id} {table} is a raster, not a table: sum_population_grid sums it over zones")
    relation = connection.read_parquet(dataset_url(dataset_id, table))
    items = []
    for column, kind in zip(relation.columns, relation.types):
        kind = str(kind)
        if kind.startswith("GEOMETRY") and any(f"'{crs}'" in kind for crs in LONGITUDE_LATITUDE):
            items.append(f"ST_SetCRS(\"{column}\", 'OGC:CRS84') AS \"{column}\"")
        elif kind.startswith("GEOMETRY") and WEB_MERCATOR in kind:
            items.append(f"ST_SetCRS(ST_Transform(\"{column}\", 'EPSG:3857', 'OGC:CRS84', always_xy := true), 'OGC:CRS84')"
                         f" AS \"{column}\"")
        else:
            items.append(f'"{column}"')
    return relation.project(", ".join(items))
