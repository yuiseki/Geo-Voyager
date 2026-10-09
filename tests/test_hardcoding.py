from geo_voyager.hardcoding import hardcoded_literals

OLD = 'import json\ndata = json.loads(previous_observations[0])\nprint(json.dumps({"count": len(data)}))'


def test_a_value_pasted_from_an_observation_is_flagged():
    new = OLD + '\nrelation_id = "1761717"'
    assert hardcoded_literals(new, OLD, ['{"name": "港区", "relation_id": "1761717"}']) == {'1761717'}


def test_a_number_pasted_from_the_critic_reason_is_flagged():
    new = OLD + '\nlimit = 943664'
    assert hardcoded_literals(new, OLD, ['理由: 人口は943664のはずだが回答は違う']) == {'943664'}


def test_a_name_pasted_from_an_observation_is_flagged():
    new = OLD + '\ntarget = "港区"'
    assert hardcoded_literals(new, OLD, ['{"name": "港区"}']) == {'港区'}


def test_keys_and_small_numbers_are_not_values():
    new = OLD + '\nkey = "relation_id"\nlimit = 3\nother = "ja"'
    assert hardcoded_literals(new, OLD, ['{"name": "港区", "relation_id": "1761717", "count": 3}']) == set()


def test_a_literal_the_original_code_already_had_is_not_new():
    old = OLD + '\nrelation_id = "1761717"'
    assert hardcoded_literals(old + '\nprint(relation_id)', old, ['{"relation_id": "1761717"}']) == set()


def test_code_that_does_not_parse_has_no_literals_to_flag():
    assert hardcoded_literals('if :\n  x', OLD, ['{"a": "1761717"}']) == set()


def test_plain_text_observations_contribute_their_numbers():
    new = OLD + '\nexpected = 459'
    assert hardcoded_literals(new, OLD, ['渋谷区の地物数は459件']) == {'459'}


def test_nested_json_values_are_found_at_any_depth():
    new = OLD + '\nx = "稚内"'
    assert hardcoded_literals(new, OLD, ['{"results": [{"name": "稚内", "pos": {"lat": 45.4}}]}']) == {'稚内'}
