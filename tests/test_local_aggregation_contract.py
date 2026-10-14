import pytest

from geo_voyager.contracts.code import local_aggregation_violations

# The comparison code from the trace: the first object named 渋谷区 was the lookup step's output, which has no count.
FROM_THE_TRACE = '''
import json
decoded = [json.loads(text) for text in previous_observations]
shibuya = next((o for o in decoded if o.get('name') == '渋谷区'), None)
shibuya_count = shibuya.get('count', 0)
'''
POSITIONAL = '''
import json
decoded = [json.loads(text) for text in previous_observations]
shibuya = decoded[2]
shinjuku = decoded[3]
'''


def test_a_missing_measurement_turned_into_zero_is_found():
    assert local_aggregation_violations(FROM_THE_TRACE) == ["shibuya.get('count', 0)"]


def test_picking_an_observation_by_its_position_is_found():
    assert local_aggregation_violations(POSITIONAL) == ['decoded[2]', 'decoded[3]']


@pytest.mark.parametrize('code,expected', [
    ('x = json.loads(previous_observations[0])', ['previous_observations[0]']),
    ('x = previous_observations[-1]', ['previous_observations[-1]']),
    ('rows = [json.loads(t) for t in previous_observations]\nlast = rows[-1]', ['rows[-1]']),
    ('rows = list(map(json.loads, previous_observations))\nfirst = rows[0]', ['rows[0]']),
    ('d = json.loads(previous_observations[1])\nprint(d)', ['previous_observations[1]']),
    ('n = o.get("count", 0.0)', ["o.get('count', 0.0)"]),
    ('n = o.get("count", None)', ["o.get('count', None)"]),
])
def test_other_forms_of_the_same_two_mistakes_are_found(code, expected):
    assert local_aggregation_violations(code) == expected


@pytest.mark.parametrize('code', [
    'decoded = [json.loads(t) for t in previous_observations]\nfor o in decoded:\n    pass',
    'decoded = [json.loads(t) for t in previous_observations]\nmatches = [o for o in decoded if o["relation_id"] == "1"]\nt = matches[0]',
    'decoded = [json.loads(t) for t in previous_observations]\nn = len(decoded)',
    'tags = o.get("tags", {})',
    'label = o.get("name", "")',
    'items = o.get("items", [])',
    'count = o["count"]',
    'v = o.get("count")',
    'for index, text in enumerate(previous_observations):\n    value = json.loads(text)\n    seen[index] = value',
    'xs = [1, 2, 3]\nfirst = xs[0]',
    'this is not python(',
    '',
])
def test_what_the_contract_allows_is_not_found(code):
    assert local_aggregation_violations(code) == []


def test_with_one_earlier_observation_its_position_is_not_a_choice():
    code = 'x = json.loads(previous_observations[0])\ny = [json.loads(t) for t in previous_observations][0]'
    assert local_aggregation_violations(code, 1) == []
    assert local_aggregation_violations(code, 2) == ['previous_observations[0]']


def test_a_defaulted_measurement_is_found_whatever_the_count():
    assert local_aggregation_violations('n = o.get("count", 0)', 1) == ["o.get('count', 0)"]


def test_observations_passed_to_a_function_are_followed_into_it():
    code = ('import json\n\n\ndef first_count(observations):\n    """Count of the first."""\n'
            '    d = [json.loads(t) for t in observations]\n    return d[0].get("count", 0)\n\n\n'
            'print(first_count(previous_observations))')
    assert sorted(local_aggregation_violations(code)) == ['d[0]', "d[0].get('count', 0)"]


def test_a_keyword_argument_is_followed_too():
    code = 'def f(xs):\n    """F."""\n    return xs[1]\n\nf(xs=previous_observations)'
    assert local_aggregation_violations(code) == ['xs[1]']


# memory_run1b, goal 4: the code made 23 area ids from the 23 wards it was given and counted footways in the first
# only (豊島区). It printed {"count": 2463}; the 23 wards have 93,108. The Critic saw the count, not the code.
FIRST_OF_THE_INPUT = '''
def count_footway(results=None):
    """Count footways in the wards."""
    wards = results["tokyo_23_ward_relation_ids"]
    area_ids = []
    for item in wards:
        relation_id = int(item["relation_id"])
        area_id = relation_id + 3600000000
        area_ids.append(area_id)
    query = f'nwr["highway"="footway"](area:{area_ids[0]});out count;'
    return query
'''


def test_the_first_row_of_an_input_is_found_through_a_loop():
    from geo_voyager.contracts.code import positional_input_picks
    assert positional_input_picks(FIRST_OF_THE_INPUT) == ['area_ids[0]']


@pytest.mark.parametrize('code, expected', [
    ('wards = results["w"]\nfirst = wards[0]', ['wards[0]']),
    ('first = results["w"][-1]', ["results['w'][-1]"]),
    ('ids = [w["id"] for w in results["w"]]\nx = ids[1]', ['ids[1]']),
])
def test_other_positional_picks_of_input_rows_are_found(code, expected):
    from geo_voyager.contracts.code import positional_input_picks
    assert positional_input_picks(code) == expected


@pytest.mark.parametrize('code', [
    'tokyo = [w for w in results["w"] if w["name"] == "東京"][0]',            # selected by a condition
    'ids = [w["id"] for w in results["w"]]\nq = ",".join(map(str, ids))',     # every row used
    'payload = json.loads(call_service("overpass"))\nn = payload["elements"][0]',  # a response, not an input
    'for w in results["w"]:\n    parts = w["name"].split()\n    head = parts[0]',  # a field of one row
])
def test_what_uses_every_row_or_selects_by_condition_is_not_found(code):
    from geo_voyager.contracts.code import positional_input_picks
    assert positional_input_picks(code) == []


# a_run3, Goal 5, steps 5 and 6: the two ward centres were the start and the end of one route. The code checked there
# were two and used both by place; the check refused it twice, and the third reply, told to select rows by name,
# wrote 世田谷区 and 大田区 into the body of the function.
START_AND_END = '''
def route_between_two_points(results, costing="auto"):
    """Route between the two points of the input."""
    centers = results["max_pair_ward_centers"]
    if len(centers) != 2:
        raise ValueError("Expected 2 ward centers")
    origin = centers[0]
    destination = centers[1]
    return route_summary(origin["lat"], origin["lon"], destination["lat"], destination["lon"], costing=costing)
'''


@pytest.mark.parametrize('code', [
    START_AND_END,
    'points = results["p"]\nassert len(points) == 2\na, b = points[0], points[1]',
    'points = results["p"]\nif 2 != len(points):\n    raise ValueError\nroute(points[1], points[0])',
    'origin, destination = results["p"]',                                      # unpacking takes every row
])
def test_every_row_used_by_place_after_checking_how_many_there_are_is_not_found(code):
    from geo_voyager.contracts.code import positional_input_picks
    assert positional_input_picks(code) == []


@pytest.mark.parametrize('code, expected', [
    ('points = results["p"]\nroute(points[0], points[1])', ['points[0]', 'points[1]']),   # how many is not checked
    ('points = results["p"]\nassert len(points) == 3\nroute(points[0], points[1])', ['points[0]', 'points[1]']),
    ('wards = results["w"]\nassert len(wards) == 23\nfirst = wards[0]', ['wards[0]']),     # one of the 23 wards
    ('points = results["p"]\nassert len(points) == 2\nroute(points[0], points[-1])', ['points[0]', 'points[-1]']),
])
def test_some_rows_by_place_are_still_found_when_how_many_is_checked(code, expected):
    from geo_voyager.contracts.code import positional_input_picks
    assert positional_input_picks(code) == expected
