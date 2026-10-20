"""The contract the Generator and the repair read for the datasets an Intent declares, made from the dataset
references and the measured schemas, not written by hand (ADR 0010)."""
from geo_voyager.contracts.tables import NAMED_AREAS, table_contract


def test_each_table_of_a_declared_dataset_is_shown_with_the_call_that_reads_it():
    text = table_contract(('yuiseki/ekidata-jp',))
    for table in ('station', 'line', 'company', 'join', 'pref'):
        assert f'read_table(connection, "yuiseki/ekidata-jp", "{table}")' in text
    assert 'read_table(connection, "yuiseki/jp-admin' not in text             # only what the Intent declared


def test_a_table_says_what_a_row_is_its_keys_the_keys_it_lacks_and_every_column():
    text = table_contract(('yuiseki/ekidata-jp',))
    assert '乗換駅は路線の数だけ行がある' in text
    assert 'station_name VARCHAR' in text and 'e_status' in text                 # every column, from the schema
    assert 'e_status（0 が運行中' in text                                        # the meaning, from the reference
    assert '持たないキー: code5' in text
    assert 'station_g_cd' in text and 'station.station_g_cd' in text            # a join key and where it joins


def test_the_boundaries_carry_the_named_areas_as_conditions_on_their_columns():
    text = table_contract(('yuiseki/jp-admin-2026-09',))
    assert NAMED_AREAS['東京23区'] == "pref_code = '13' AND name LIKE '%区'"
    assert '東京23区: filter("pref_code = \'13\' AND name LIKE \'%区\'")' in text
    assert 'geometry は OGC:CRS84' in text


def test_a_raster_is_read_by_the_zonal_sum_not_by_read_table():
    text = table_contract(('yuiseki/worldpop-jp-2026-01',))
    assert 'read_table(connection, "yuiseki/worldpop-jp-2026-01", "population_100m_2020")' not in text
    assert 'sum_population_grid(connection, zones)' in text


def test_the_contract_fits_beside_the_rest_of_the_prompt():
    # 4,500 when the context was 8,192 tokens; 16,384 now, with the join keys' notes (2026-10-14) and how to measure
    # (577 characters, 2026-10-15). The longest code prompt of the small tasks was 9,743 tokens.
    assert len(table_contract(('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp'))) < 5500


def test_a_join_key_says_how_to_cast_it_and_a_column_how_a_value_is_missing():
    text = table_contract(('yuiseki/ekidata-jp',))
    assert 'cast(pref_cd as integer)' in text                                   # pref_code is a 2-digit string there
    assert "'0000-00-00'" in text                                                 # open_ymd with no date


def test_a_table_split_by_a_column_says_to_filter_on_it():
    text = table_contract(('yuiseki/jp-admin-2026-09',))
    assert 'pref_code ごとに 47 の塊' in text
    assert '180 秒' in text


def test_a_column_note_is_shown_even_for_the_geometry():
    # Measured in GeoAI-master-skills (2026-10-14): neighbouring boundaries overlap, and ST_Touches misses 8 in 10 pairs.
    text = table_contract(('yuiseki/jp-admin-2026-09',))
    assert 'geometry（' in text
    assert 'ST_Intersects' in text


def test_the_population_grid_says_how_its_catalog_and_its_pixels_are_read():
    # GeoAI-master-skills' small task 11 (2026-10-15), three runs: the Generator looked for the grid in the files catalog
    # with sex = 'total' (the total population's sex is NULL), found no row and stopped; another read too much and
    # was killed at 1 GB. Measured through the Gateway in the sandbox the same day.
    text = table_contract(('yuiseki/worldpop-jp-2026-01',))
    assert "sex = 'total' で絞ると 0 行" in text and '126,574,853' in text
    assert "rasterio.open('/vsicurl/' + dataset_url('yuiseki/worldpop-jp-2026-01'))" in text
    assert '3.8 GB' in text and '窓' in text


LAND_PRICE = 'yuiseki/ksj-l01-land-price'


def test_the_land_prices_are_read_for_their_latest_year_at_the_cards_revision():
    # The reference reads parquet/<year>.parquet. Geo-Voyager reads the latest year, 2026: a row has its change from
    # the year before (change_pct), and the other years' original columns differ in number and meaning.
    from geo_voyager.dataset_tables import TABLE_URLS
    url = TABLE_URLS[(LAND_PRICE, 'land_price')]
    assert url.startswith('https://huggingface.co/datasets/yuiseki/ksj-l01-land-price/resolve/7e32fd1')
    assert url.endswith('/parquet/2026.parquet')


def test_columns_that_differ_only_by_their_number_are_shown_as_one_range():
    text = table_contract((LAND_PRICE,))
    assert 'price_yen BIGINT' in text and 'municipality_code VARCHAR' in text
    assert 'L01_001〜L01_148 VARCHAR（148 列）' in text and 'L01_002 VARCHAR' not in text
    assert 'price_yen（公示価格 (円/m²)）' in text
    assert len(text) < 4500


def test_the_land_prices_are_in_the_catalog_the_curriculum_and_the_planner_see():
    from geo_voyager.datasets import load_readable_dataset_graph
    assert LAND_PRICE in [dataset.id for dataset in load_readable_dataset_graph().all()]


OSM_TOKYO = 'yuiseki/osm-tokyo23-src-2026-08'


def test_a_table_with_the_columns_of_one_shown_before_points_to_it_and_names_only_the_difference():
    # osm2pgsql's four tables share about 70 columns; listed for each, they were 6,667 characters.
    text = table_contract((OSM_TOKYO,))
    assert text.count('amenity VARCHAR') == 1
    assert '列: planet_osm_polygon と同じ' in text
    point = text[text.index('"planet_osm_point"'):]
    point = point[:point.index('read_table(', 1)] if 'read_table(' in point[1:] else point
    assert 'ele VARCHAR' in point and 'way_area' in point                       # the difference, both ways
    assert len(text) < 4500


def test_a_web_mercator_geometry_is_said_to_come_back_in_longitude_and_latitude():
    text = table_contract((OSM_TOKYO,))
    polygon = text[:text.index('"planet_osm_point"')]
    assert 'way は read_table が OGC:CRS84' in polygon and 'bbox は EPSG:3857 のメートルのまま' in polygon


def test_a_column_named_as_a_keyword_of_sql_is_said_to_be_quoted():
    # natural = 'sand' is a syntax error in DuckDB: four candidates failed on it in a Goal of explore 27.
    text = table_contract((OSM_TOKYO,))
    assert text.count('"natural"') == 1 and '二重引用符' in text
    assert '"amenity"' not in text
    assert '二重引用符' not in table_contract((LAND_PRICE,))


def test_a_tag_read_from_tags_when_it_has_its_own_column_is_refused():
    # Explore 33: asked how many power=plant areas the 23 wards have, the code read tags->>'power' six times and found
    # none; osm2pgsql puts power in its own column, and the 7 areas have no power in tags.
    from geo_voyager.contracts.tables import tag_column_problems
    osm = ('yuiseki/osm-tokyo23-src-2026-08',)
    for code in ("polygons.filter(\"(tags->>'power') = 'plant'\")",
                 "connection.sql(\"SELECT count(*) FROM p WHERE json_extract_string(tags, '$.power') = 'plant'\")",
                 "connection.sql(\"SELECT tags->'power' FROM p\")"):
        found = tag_column_problems(code, osm)
        assert found and '"power"' in found[0] and 'tags' in found[0], code
    assert tag_column_problems("polygons.filter(\"tags->>'cuisine' = 'ramen'\")", osm) == []   # not a column
    assert tag_column_problems("polygons.filter(\"power = 'plant'\")", osm) == []
    assert tag_column_problems("polygons.filter(\"(tags->>'power') = 'plant'\")", ('yuiseki/ekidata-jp',)) == []


def test_code_reading_only_the_points_of_a_kind_that_has_areas_is_refused():
    # Explores 37 and 39: shop=watches of 大田区 (3 of 4 are areas) and amenity=photo_booth of 港区 and 新宿区 (3 of 10)
    # were read from planet_osm_point alone; the photo booths' average price came out 6.2 million yen, not 14.8.
    from geo_voyager.contracts.tables import point_only_problems
    code = 'points = read_table(connection, "yuiseki/osm-tokyo23-src-2026-08", "planet_osm_point").filter("amenity = \'photo_booth\'")'
    found = point_only_problems(code, '港区と新宿区内の amenity=photo_booth の OSM 地物について平均を求める')
    assert len(found) == 1 and 'amenity=photo_booth' in found[0] and 'planet_osm_polygon' in found[0]
    both = code + '\npolygons = read_table(connection, "yuiseki/osm-tokyo23-src-2026-08", "planet_osm_polygon")'
    assert point_only_problems(both, '港区と新宿区内の amenity=photo_booth の OSM 地物') == []
    assert point_only_problems(code, '港区の写真機の件数') == []                            # no kind named


def test_a_kind_mostly_points_read_from_the_areas_alone_is_refused():
    # Explore 44: office=government of 杉並区 and 江戸川区 read from planet_osm_polygon alone; 273 of the 331 in the 23
    # wards are points, and the sums came out the other way round (杉並区 has 10, 江戸川区 5).
    from geo_voyager.contracts.tables import polygon_only_problems
    code = ('offices = read_table(connection, "yuiseki/osm-tokyo23-src-2026-08", "planet_osm_polygon")'
            '.filter("office = \'government\'")')
    intent = "杉並区と江戸川区の tags->>'office'='government' の要素ごとに、半径 1 km の推計人口を合計する"
    found = polygon_only_problems(code, intent)
    assert len(found) == 1 and 'office=government' in found[0] and 'planet_osm_point' in found[0]
    both = code + '\npoints = read_table(connection, "yuiseki/osm-tokyo23-src-2026-08", "planet_osm_point")'
    assert polygon_only_problems(both, intent) == []
    # the areas are what an Intent on the area of a kind asks for
    assert polygon_only_problems(code, '杉並区の office=government の面積の合計を求める') == []
    assert polygon_only_problems(code, '杉並区の office=government の面の件数を数える') == []
    assert polygon_only_problems(code, '台東区の office=government を持つ way の個数を数える') == []
    assert len(polygon_only_problems(code, '杉並区の境界面と office=government を空間結合する')) == 1
