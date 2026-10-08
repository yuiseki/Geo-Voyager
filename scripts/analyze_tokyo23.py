"""固定の東京23区実験。データへの接続先は Gateway だけ。"""

from geo_voyager.control_primitives import connect_duckdb as connect, load_admin_units

def analyze(connection):
    rows = load_admin_units('yuiseki/jp-admin-2026-09', connection, area='東京都23区').fetchall()
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
