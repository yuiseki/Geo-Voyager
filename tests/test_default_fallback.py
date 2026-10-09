import pytest

from geo_voyager.default_fallback import introduced_fallbacks

ORIGINAL = '''import json
data = json.loads(response)
rows = [{"value": item["value"], "count": item["count_all"]} for item in data["data"]]
print(json.dumps(rows))'''
KEY_ERROR = "Traceback (most recent call last):\n  File \"<candidate>\", line 3, in <module>\nKeyError: 'count_all'"


def repaired(line):
    return ORIGINAL.replace('item["count_all"]', line)


# ---- a missing required value must stay an error

@pytest.mark.parametrize('replacement', [
    'item.get("count_all", 0)', 'item.get("count_all", "")', 'item.get("count_all", [])',
    'item.get("count_all", None)', 'item.get("count_all", {})', 'item.get("count_all")',
    'item.get("count_all", len(data))',
])
def test_replacing_a_required_key_by_a_get_is_refused_whatever_the_default(replacement):
    found = introduced_fallbacks(ORIGINAL, repaired(replacement), KEY_ERROR)
    assert len(found) == 1 and 'count_all' in found[0]


def test_a_repair_for_another_failure_is_not_judged_by_this_rule():
    """The rule is about a failure that is a missing key or index. Any other failure is answered differently."""
    assert introduced_fallbacks(ORIGINAL, repaired('item.get("count_all", 0)'), 'ValueError: bad') == []
    assert introduced_fallbacks(ORIGINAL, repaired('item.get("count_all", 0)'), '') == []


def test_only_the_key_the_traceback_names_counts_as_hidden():
    other = ORIGINAL.replace('item["value"]', 'item.get("value", "")')
    assert introduced_fallbacks(ORIGINAL, other.replace('item["count_all"]', 'item["count"]'), KEY_ERROR) == []
    assert introduced_fallbacks(ORIGINAL, repaired('item.get("count_all", 0)'), "KeyError: 'value'") == []


def test_the_required_key_is_known_from_the_traceback_even_when_the_original_got_it_another_way():
    original = 'row = fetch()\nvalue = getattr(row, "x")\nprint(row["count_all"])'
    fixed = 'row = fetch()\nvalue = getattr(row, "x")\nprint(row.get("count_all", 0))'
    assert introduced_fallbacks(original, fixed, "KeyError: 'count_all'") != []


def test_a_nested_required_key_is_refused_too():
    assert introduced_fallbacks(ORIGINAL, ORIGINAL.replace('data["data"]', 'data.get("data", [])'), "KeyError: 'data'") != []


# ---- fixing the key is what is wanted

def test_changing_the_key_to_the_one_the_api_really_has_is_allowed():
    assert introduced_fallbacks(ORIGINAL, repaired('item["count"]'), KEY_ERROR) == []


def test_other_ways_of_fixing_the_failure_are_allowed():
    fixed = ORIGINAL.replace('response)', 'response.strip())')
    assert introduced_fallbacks(ORIGINAL, fixed, 'ValueError: bad') == []
    assert introduced_fallbacks(ORIGINAL, repaired('item["count"]') + '\nassert rows, "no rows"', KEY_ERROR) == []


# ---- an optional field is not a required one

def test_a_get_that_was_already_in_the_original_is_not_new():
    original = 'remark = r.get("remark")\ncount = int(r["total"])\nprint(count, remark)'
    assert introduced_fallbacks(original, original.replace('int(r["total"])', 'int(r["count"])'), "KeyError: 'total'") == []


def test_an_existing_get_with_a_default_is_left_alone_even_if_the_repair_edits_around_it():
    original = 'n = item.get("count", 0)\nv = item["value"]\nprint(n, v)'
    fixed = 'n = item.get("count", 0)\nv = item["label"]\nprint(n, v)'
    assert introduced_fallbacks(original, fixed, "KeyError: 'value'") == []


def test_a_new_get_on_a_key_the_original_never_required_is_allowed():
    fixed = ORIGINAL + '\nremark = data.get("remark")\nif remark:\n    raise RuntimeError(remark)'
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == []


def test_a_get_on_something_that_is_not_a_subscripted_key_is_allowed():
    fixed = ORIGINAL.replace('print(json.dumps(rows))', 'print(json.dumps(rows), os.environ.get("X", ""))')
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == []


# ---- swallowing the error is the same thing

def test_a_new_handler_that_swallows_a_missing_key_is_refused():
    fixed = ORIGINAL.replace('rows = [{"value": item["value"], "count": item["count_all"]} for item in data["data"]]',
                             'rows = []\nfor item in data["data"]:\n    try:\n        rows.append({"value": item["value"], "count": item["count_all"]})\n    except KeyError:\n        pass')
    found = introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR)
    assert found and 'KeyError' in found[0]


@pytest.mark.parametrize('handler', ['except:', 'except Exception:', 'except (KeyError, IndexError):'])
def test_a_new_broad_handler_without_a_raise_is_refused(handler):
    fixed = f'try:\n    {ORIGINAL.splitlines()[2]}\n{handler}\n    rows = []\nprint(1)'
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) != []


def test_a_handler_that_raises_again_is_not_swallowing():
    fixed = 'import json\ndata = json.loads(response)\ntry:\n    rows = [item["count"] for item in data["data"]]\nexcept KeyError as error:\n    raise RuntimeError("schema changed") from error'
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == []


def test_a_handler_for_an_unrelated_error_is_allowed():
    fixed = ORIGINAL.replace('data = json.loads(response)', 'try:\n    data = json.loads(response)\nexcept ValueError:\n    raise')
    assert introduced_fallbacks(ORIGINAL, fixed, 'ValueError') == []


def test_a_handler_that_was_already_in_the_original_is_not_new():
    original = 'try:\n    x = d["a"]\nexcept KeyError:\n    x = 0\nprint(d["b"])'
    assert introduced_fallbacks(original, original.replace('d["b"]', 'd["c"]'), "KeyError: 'b'") == []


# ---- robustness

def test_code_that_does_not_parse_has_nothing_to_report():
    assert introduced_fallbacks(ORIGINAL, 'if :\n  x', KEY_ERROR) == []
    assert introduced_fallbacks('if :', ORIGINAL, KEY_ERROR) == []


def test_each_fallback_is_reported_once_with_the_code_that_was_written():
    fixed = ORIGINAL.replace('item["count_all"]', 'item.get("count_all", 0)')
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == ["item.get('count_all', 0)"]


# ---- a one-argument get is fine when the missing value is then checked out loud

@pytest.mark.parametrize('check', [
    'if count is None:\n    raise ValueError("count is missing")',
    'if not count:\n    raise ValueError("count is missing")',
    'assert count is not None, "count is missing"',
])
def test_a_one_argument_get_followed_by_an_explicit_check_is_not_hiding_anything(check):
    fixed = ORIGINAL.replace('rows = [{"value": item["value"], "count": item["count_all"]} for item in data["data"]]',
                             'rows = []\nfor item in data["data"]:\n    count = item.get("count_all")\n    ' + check.replace('\n', '\n    ')
                             + '\n    rows.append({"value": item["value"], "count": count})')
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == []


def test_a_one_argument_get_that_is_not_checked_is_hiding_the_value():
    fixed = ORIGINAL.replace('item["count_all"]', 'item.get("count_all")')
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == ["item.get('count_all')"]


def test_a_default_is_hidden_even_when_something_is_checked_later():
    fixed = ORIGINAL.replace('item["count_all"]', 'item.get("count_all", 0)') + '\nassert rows'
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == ["item.get('count_all', 0)"]


def test_an_explicit_membership_test_is_how_a_really_optional_field_is_handled():
    fixed = ORIGINAL.replace('"count": item["count_all"]}', '"count": item["count"] if "count" in item else None}')
    assert introduced_fallbacks(ORIGINAL, fixed, KEY_ERROR) == []
