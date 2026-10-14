from geo_voyager.output_contract import output_problem

# memory_run2 goal 1: the rows of ekidata are a station on a line, so 東京 came back once per line.
STATIONS = ('[{"name": "東京", "lat": 35.681391, "lon": 139.766103}, {"name": "渋谷", "lat": 35.658034, "lon": 139.701636}, '
            '{"name": "東京", "lat": 35.681391, "lon": 139.766103}, {"name": "東京", "lat": 35.681391, "lon": 139.766103}]')


def test_rows_that_are_the_same_are_a_problem_that_says_how_many():
    problem = output_problem(STATIONS)
    assert '2 行' in problem and '重複' in problem and '"東京"' in problem


def test_the_rows_of_a_list_under_a_key_are_checked_too():
    assert output_problem('{"pairs": [{"a": 1}, {"a": 1}], "count": 2}') is not None


def test_rows_that_differ_and_output_that_is_not_a_list_pass():
    assert output_problem('[{"name": "東京", "line": "山手線"}, {"name": "東京", "line": "中央線"}]') is None
    assert output_problem('{"count": 57}') is None
    assert output_problem('not json') is None
    assert output_problem('[1, 1, 2]') is None        # numbers are values, not rows
