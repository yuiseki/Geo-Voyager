"""The sphere and spheroid functions of this DuckDB read a point as latitude, longitude; read_table gives longitude,
latitude. Measured on DuckDB 1.5.6 (2026-10-15): from Tokyo to Osaka, 396 km, ST_Distance_Sphere without the
coordinates flipped says 473 km, and ST_Area_Spheroid of Japan is NaN. Nothing fails; the value is wrong.

The small tasks of GeoAI-skills, task 17: the Generator called ST_Area_Spheroid on Natural Earth's countries.
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
    # GeoAI-skills' small task 11 (2026-10-15): told that cog_path can not be read, the Generator opened
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
