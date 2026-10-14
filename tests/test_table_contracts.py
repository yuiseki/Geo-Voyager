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
    # Measured in GeoAI-skills (2026-10-14): neighbouring boundaries overlap, and ST_Touches misses 8 in 10 pairs.
    text = table_contract(('yuiseki/jp-admin-2026-09',))
    assert 'geometry（' in text
    assert 'ST_Intersects' in text


def test_the_population_grid_says_how_its_catalog_and_its_pixels_are_read():
    # GeoAI-skills' small task 11 (2026-10-15), three runs: the Generator looked for the grid in the files catalog
    # with sex = 'total' (the total population's sex is NULL), found no row and stopped; another read too much and
    # was killed at 1 GB. Measured through the Gateway in the sandbox the same day.
    text = table_contract(('yuiseki/worldpop-jp-2026-01',))
    assert "sex = 'total' で絞ると 0 行" in text and '126,574,853' in text
    assert "rasterio.open('/vsicurl/' + dataset_url('yuiseki/worldpop-jp-2026-01'))" in text
    assert '3.8 GB' in text and '窓' in text
