import pytest

from geo_voyager.local_aggregation_contract import local_aggregation_violations

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
