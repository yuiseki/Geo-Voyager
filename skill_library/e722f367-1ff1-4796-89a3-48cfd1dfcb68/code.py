from geo_voyager.control_primitives import connect_duckdb, load_admin_units
with connect_duckdb() as connection:
    units = load_admin_units(dataset_id, connection, area="東京都23区")
    # AOI指定済みの区域から人口最小の1件を取得
    result = units.order("population ASC").limit(1)
    row = result.fetchone()
    if row:
        code5, name, population = row
        print(f"東京都23区で人口が最も少ない区は '{name}' (code5: {code5}) で、人口は {population} 人です。")
    else:
        print("該当するデータが見つかりませんでした。")