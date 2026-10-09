from bench.run_goals import pending_runs


def test_pending_runs_are_round_major_and_skip_what_is_recorded():
    done = [{'id': 'a', 'round': 1}, {'id': 'b', 'round': 2}]
    assert pending_runs(['a', 'b'], 2, done) == [('b', 1), ('a', 2)]


def test_nothing_is_pending_when_everything_is_recorded():
    rows = [{'id': g, 'round': r} for g in 'ab' for r in (1, 2)]
    assert pending_runs(['a', 'b'], 2, rows) == []


def test_a_leftover_directory_from_an_interrupted_run_is_set_aside(tmp_path):
    from bench.run_goals import set_aside
    stale = tmp_path / 'a.r1'
    stale.mkdir(); (stale / 'llm_01_prompt.txt').write_text('partial')
    set_aside(stale)
    assert not stale.exists()
    kept = list(tmp_path.glob('a.r1.interrupted*'))
    assert len(kept) == 1 and (kept[0] / 'llm_01_prompt.txt').read_text() == 'partial'


def test_set_aside_does_nothing_without_a_leftover(tmp_path):
    from bench.run_goals import set_aside
    set_aside(tmp_path / 'missing')
    assert list(tmp_path.iterdir()) == []
