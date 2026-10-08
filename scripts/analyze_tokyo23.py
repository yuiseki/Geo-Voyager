"""固定の東京23区実験。データへの接続先は Gateway だけ。"""

from geo_voyager.control_primitives import connect_duckdb as connect, dataset_url

GATEWAY_URL = dataset_url("yuiseki/jp-admin-2026-09")



def analyze(connection):
    rows = connection.execute(
        "SELECT code5, name, population FROM read_parquet(?) "
        "WHERE code5 BETWEEN '13101' AND '13123'",
        [GATEWAY_URL],
    ).fetchall()
    if len(rows) != 23:
        raise ValueError(f"Expected 23 wards, got {len(rows)}")
    if any(type(population) is not int for _, _, population in rows):
        raise TypeError("population must be an integer")
    return len(rows), sum(population for _, _, population in rows)


if __name__ == "__main__":
    with connect() as connection:
        count, total = analyze(connection)
    print(f"rows={count}")
    print(f"population_total={total}")
