"""The contract the Generator and the repair read for the datasets an Intent declares, made from the dataset
references and the measured schemas, not written by hand (ADR 0010)."""
from geo_voyager.table_contracts import NAMED_AREAS, table_contract


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
    assert len(table_contract(('yuiseki/jp-admin-2026-09', 'yuiseki/ekidata-jp'))) < 4500
