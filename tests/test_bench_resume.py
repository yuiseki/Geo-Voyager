from bench.run_goals import pending_runs


def test_pending_runs_are_round_major_and_skip_what_is_recorded():
    done = [{'id': 'a', 'round': 1}, {'id': 'b', 'round': 2}]
    assert pending_runs(['a', 'b'], 2, done) == [('b', 1), ('a', 2)]


def test_nothing_is_pending_when_everything_is_recorded():
    rows = [{'id': g, 'round': r} for g in 'ab' for r in (1, 2)]
    assert pending_runs(['a', 'b'], 2, rows) == []
