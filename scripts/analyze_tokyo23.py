"""固定の東京23区実験。データへの接続先は Gateway だけ。"""

from geo_voyager.control_primitives import connect_duckdb as connect, read_table

# The 23 wards, as geo_voyager.contracts.tables.NAMED_AREAS names them.
TOKYO_23 = "pref_code = '13' AND name LIKE '%区'"

def analyze(connection):
    rows = read_table(connection, 'yuiseki/jp-admin-2026-09', 'municipalities').filter(TOKYO_23).project(
        'code5, name, population').fetchall()
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
