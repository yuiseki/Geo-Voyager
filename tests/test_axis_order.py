"""The sphere and spheroid functions of this DuckDB read a point as latitude, longitude; read_table gives longitude,
latitude. Measured on DuckDB 1.5.6 (2026-10-15): from Tokyo to Osaka, 396 km, ST_Distance_Sphere without the
coordinates flipped says 473 km, and ST_Area_Spheroid of Japan is NaN. Nothing fails; the value is wrong.

The small tasks of GeoAI-master-skills, task 17: the Generator called ST_Area_Spheroid on Natural Earth's countries.
"""
import pytest

from geo_voyager.contracts.code import axis_order_problems
from geo_voyager.contracts.tables import table_contract


@pytest.mark.parametrize('function', ['ST_Distance_Sphere', 'ST_Area_Spheroid', 'ST_Distance_Spheroid',
                                      'ST_Length_Spheroid', 'ST_Perimeter_Spheroid', 'ST_DWithin_Spheroid'])
def test_a_sphere_function_on_unflipped_coordinates_is_refused(function):
    code = f'connection.sql("SELECT {function}(a.geometry, b.geometry) FROM a, b")'
    found = axis_order_problems(code)
    assert found and function in found[0] and 'ST_FlipCoordinates' in found[0]


def test_the_coordinates_flipped_pass():
    code = 'connection.sql("SELECT ST_Distance_Sphere(ST_FlipCoordinates(a.geometry), ST_FlipCoordinates(b.geometry)) FROM a, b")'
    assert axis_order_problems(code) == []


def test_measuring_in_a_projected_system_passes():
    code = ("connection.sql(\"SELECT ST_Area(ST_Transform(geometry, 'OGC:CRS84', 'EPSG:6933')) / 1e6 AS area_km2 FROM c\")")
    assert axis_order_problems(code) == []


def test_the_generator_is_told_how_to_measure_an_area_a_distance_and_a_circle():
    text = table_contract(('yuiseki/natural-earth',))
    assert "ST_Area(ST_Transform(geometry, 'OGC:CRS84', 'EPSG:6933'))" in text
    assert 'ST_Distance_Sphere(ST_FlipCoordinates(a), ST_FlipCoordinates(b))' in text
    assert "'EPSG:' || (32601 + CAST(floor((ST_X(geometry) + 180) / 6) AS INTEGER))" in text and '度のまま' in text


def test_the_population_grids_catalog_path_is_refused_as_what_rasterio_opens():
    # GeoAI-master-skills' small task 11 (2026-10-15): told that cog_path can not be read, the Generator opened
    # '/vsicurl/' + cog_path and failed on the host "cog".
    from geo_voyager.contracts.code import catalog_path_problems
    bad = "rasterio.open('/vsicurl/' + files.project('cog_path').fetchone()[0])"
    good = "rasterio.open('/vsicurl/' + dataset_url('yuiseki/worldpop-jp-2026-01'))"
    assert catalog_path_problems(bad) and 'dataset_url' in catalog_path_problems(bad)[0]
    assert catalog_path_problems(good) == []


def test_the_generator_refuses_code_with_a_sphere_function_on_unflipped_coordinates():
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import contract_problems
    code = ('from geo_voyager.control_primitives import connect_duckdb, read_table\n\n\n'
            'def areas():\n    """Areas."""\n    with connect_duckdb() as connection:\n'
            '        countries = read_table(connection, "yuiseki/natural-earth", "ne_10m_admin_0_countries")\n'
            '        return countries.project("ADM0_A3, ST_Area_Spheroid(geometry) / 1e6 AS area_km2").fetchall()\n')
    problems = contract_problems(Intent('国の面積', dataset_ids=('yuiseki/natural-earth',)), code)
    assert any('ST_Area_Spheroid' in problem for problem, _ in problems)


def test_a_relation_put_into_the_sql_with_an_f_string_is_refused():
    # Explore 36 (and 13, 23, 32, 33): FROM {wards} put the relation's printed table into the SQL, a syntax error.
    from geo_voyager.contracts.code import relation_in_sql_problems
    code = ('wards = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities").filter("name = \'北区\'")\n'
            'helipads = wards.filter("x")\n'
            'connection.sql(f"SELECT * FROM {helipads} h JOIN wards w ON ST_Within(h.way, w.geometry) WHERE h.aeroway = \'{value}\'")')
    found = relation_in_sql_problems(code)
    assert len(found) == 1 and 'helipads' in found[0] and 'FROM helipads' in found[0]
    assert relation_in_sql_problems(code.replace('{helipads}', 'helipads')) == []
    assert relation_in_sql_problems('n = 3\nconnection.sql(f"SELECT {n}")') == []
    rows = 'rows = connection.sql("SELECT 1").fetchall()\nprint(f"{rows}")'
    assert relation_in_sql_problems(rows) == []


def test_a_key_the_target_does_not_have_is_refused():
    # Explore 35 and 37: the code read intent_target["relation_id"]; the target has name, id_type and id_value, and the
    # KeyError took two steps each time.
    from geo_voyager.contracts.code import target_key_problems
    code = ('def f(intent_target):\n'
            '    relation = intent_target\n'
            '    area_id = int(relation["relation_id"]) + 3600000000\n'
            '    return intent_target.get("osm_id"), intent_target["name"]\n')
    found = target_key_problems(code)
    assert len(found) == 2 and 'relation_id' in found[0] and 'osm_id' in found[1] and 'id_value' in found[0]
    assert target_key_problems('x = int(intent_target["id_value"]) + 1\ny = intent_target.get("id_type")') == []
    # a name bound again to something else is no longer the target
    assert target_key_problems('intent_target = json.loads(s)\nintent_target["relation_id"]') == []
    # a guess that falls back when wrong runs: a default, or a key asked after first (saved skills of explores 4, 6, 10)
    assert target_key_problems('key = intent_target.get("key", "railway")') == []
    assert target_key_problems('if "relation_id" in intent_target:\n    r = intent_target["relation_id"]') == []


def test_a_geometry_read_out_of_a_row_and_put_into_the_sql_is_refused():
    # Explores 36 and 41: a geometry read with fetchone() is WKB bytes; put into the SQL with an f-string it was a
    # syntax error, three steps in explore 41.
    from geo_voyager.contracts.code import relation_in_sql_problems
    code = ('town = read_table(connection, "yuiseki/jp-admin-2026-09", "municipalities").filter("name = \'双葉町\'")\n'
            'rep_lon, rep_lat, town_geometry = town.project("rep_lon, rep_lat, geometry").fetchone()\n'
            'connection.sql(f"SELECT * FROM stations s WHERE ST_Within(s.geometry, {town_geometry}) AND {rep_lon} > 0")')
    found = relation_in_sql_problems(code)
    assert len(found) == 1 and 'town_geometry' in found[0] and 'JOIN' in found[0]
    row = ('row = units.project("code5, population, geometry").fetchone()\ncode5, population, geometry = row\n'
           'connection.sql(f"SELECT ST_Area(\'{geometry}\')")')
    assert len(relation_in_sql_problems(row)) == 1
