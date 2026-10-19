"""Code may not carry a code or an id that nobody gave it (geo_voyager.contracts.references.unsourced_numbers).

Exploration 13 (2026-10-17) wrote the municipal codes of the wards from memory six times in 894 pieces of code, and all
six were wrong: Itabashi as 13106 (Taito's), Kita as 13111 (Ota's) and 13105 (Bunkyo's), Itabashi and Meguro as 13115
and 13116, Kohoku as 14104. The Planner's Intents were already held to this (a24bf36); the code was not.
"""
from geo_voyager.contracts.references import unsourced_numbers
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate_generator import contract_problems


def test_a_municipal_code_written_from_memory_is_found():
    code = 'def f(results):\n    return read(filter="municipality_code = \'13106\'")\n'
    assert unsourced_numbers(code, '板橋区の標準地') == ['13106']


def test_a_code_given_by_the_intent_or_an_earlier_observation_is_not():
    code = 'def f(results):\n    return read(code5="13119")\n'
    assert unsourced_numbers(code, '板橋区（code5 13119）') == []


def test_comments_round_numbers_and_epsg_codes_are_not_codes():
    code = ('def f(results):\n'
            '    # 板橋区の municipality_code は 13106\n'
            '    area = 3600000000 + int(results["relation_id"])\n'
            '    return transform(x, "EPSG:32654") / 1000000\n')
    assert unsourced_numbers(code, '') == []


def test_a_value_written_into_the_code_is_found_too():
    # explore11 Goal 20 wrote an earlier finding's estimate as a default argument.
    assert unsourced_numbers('def f(results, worldpop_population=3779446):\n    return 1\n', '') == ['3779446']


def test_the_generator_sends_such_code_back():
    intent = Intent('板橋区の標準地の数を数える', dataset_ids=('yuiseki/ksj-l01-land-price',),
                    previous_observations=(Observation('{"name": "北区", "code5": "13117"}'),))
    code = ('from geo_voyager.control_primitives import read_table\n\n'
            'def count_lots(connection):\n    """Count."""\n'
            '    return read_table(connection, "yuiseki/ksj-l01-land-price", "land_price")'
            '.filter("municipality_code in (\'13117\', \'13106\')").count("*").fetchone()[0]\n')
    found = ' '.join(found for found, _ in contract_problems(intent, code))
    assert '13106' in found and '13117' not in found


def test_the_constants_of_the_earth_are_not_codes():
    # Exploration 16 (2026-10-18) was sent back for metres in a degree, 111320, which nobody need give.
    code = 'def f(a, lat):\n    return a * 111320 * 111320 + 6371000 + 6378137 + 111319\n'
    assert unsourced_numbers(code, '') == []


def test_a_longitude_or_latitude_in_japan_written_from_memory_is_found():
    # Explore 28: given the representative points of 台東区 and 江戸川区 (35.712607, 139.779984 and 35.706648,
    # 139.868312), the code routed between points it made up in its defaults, and walked 55 minutes, not 107.
    code = 'def f(results, taito_lat=35.715, taito_lon=139.796, edogawa_lat=35.665):\n    return route(taito_lat)\n'
    given = '[{"name": "台東区", "rep_lon": 139.779984, "rep_lat": 35.712607}]'
    assert unsourced_numbers(code, given) == ['35.715', '139.796', '35.665']
    assert unsourced_numbers('def f(results):\n    return route(35.712607, 139.779984)\n', given) == []


def test_other_decimals_are_not_coordinates():
    code = 'def f(results):\n    return {"ratio": round(x * 0.25, 2), "km": 12.5, "pct": 99.95, "lon": 160.25}\n'
    assert unsourced_numbers(code, '') == []
