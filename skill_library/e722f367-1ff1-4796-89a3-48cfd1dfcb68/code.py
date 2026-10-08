from geo_voyager.control_primitives import connect_duckdb, load_admin_units
with connect_duckdb() as connection:
    units = load_admin_units(dataset_id, connection)
    # 東京都23区の範囲で絞り込み、人口の昇順でソートし、最小値の1件を取得
    result = units.filter("code5 >= '13101' AND code5 <= '13123'").order("population ASC").limit(1)
    row = result.fetchone()
    if row:
        code5, name, population = row
        print(f"東京都23区で人口が最も少ない区は '{name}' (code5: {code5}) で、人口は {population} 人です。")
    else:
        print("該当するデータが見つかりませんでした。")