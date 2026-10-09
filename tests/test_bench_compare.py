import pytest

from bench.compare import compare, fisher_exact


def test_fisher_exact_matches_the_known_two_sided_value():
    # The classic 2x2 table [[3, 1], [1, 3]] has a two-sided p of 0.4857.
    assert fisher_exact(3, 1, 1, 3) == pytest.approx(0.4857, abs=1e-4)


def test_fisher_exact_is_one_for_identical_proportions_and_symmetric():
    assert fisher_exact(5, 5, 5, 5) == pytest.approx(1.0)
    assert fisher_exact(8, 2, 3, 7) == pytest.approx(fisher_exact(3, 7, 8, 2))


def test_fisher_exact_is_small_for_a_large_difference():
    assert fisher_exact(20, 0, 0, 20) < 1e-6


def step(**overrides):
    base = {'intent': 's', 'outcome_at': 0, 'candidate_attempts': 1, 'failure_types': [], 'oscillation': False,
            'critic_success': True, 'observation_head': '', 'services': ['overpass'], 'datasets': [],
            'requires_context': False, 'reused_skill_failed': False, 'reused_skill_succeeded': False}
    base.update(overrides)
    return base


def row(goal, correct, steps, **overrides):
    base = {'id': goal, 'round': 1, 'correct': correct, 'goal_critic_success': correct, 'intents': steps,
            'required': ['overpass'], 'target_relation': None, 'elapsed': 10.0}
    base.update(overrides)
    return base


def failing_step(**overrides):
    return step(outcome_at=None, candidate_attempts=3, failure_types=['data_shape'] * 3, critic_success=False, **overrides)


def test_compare_reports_each_side_and_the_difference():
    old = [row('a', False, [step(), failing_step()]), row('a', False, [failing_step()]), row('b', True, [step()])]
    new = [row('a', True, [step()]), row('a', True, [step()]), row('b', True, [step()])]
    result = compare(old, new)
    assert result['old']['correct'] == 1 and result['new']['correct'] == 3
    assert result['old']['measured'] == 3
    assert result['difference']['correct_rate'] == pytest.approx(2 / 3)
    assert 0 < result['difference']['fisher_p'] <= 1


def test_compare_counts_early_step_failures_as_a_share_of_measured_runs():
    old = [row('a', False, [failing_step()]), row('a', False, [step(), failing_step()]),
           row('a', False, [step(), step(), step(), failing_step()]), row('a', True, [step()])]
    result = compare(old, old)['old']
    assert result['step12_failure_rate'] == 0.5  # steps 1 and 2 of 4 measured runs


def test_compare_includes_per_goal_pairs_and_planner_variance():
    old = [row('a', False, [step()]), row('a', False, [step(), step()])]
    new = [row('a', True, [step()]), row('a', True, [step()])]
    result = compare(old, new)
    assert result['by_goal']['a'] == {'old': '0/2', 'new': '2/2'}
    assert result['planner']['old']['mean_distinct_plans'] == 2
    assert result['planner']['new']['mean_distinct_plans'] == 1


def test_up_to_round_keeps_only_the_complete_rounds_asked_for():
    from bench.compare import up_to_round
    rows = [{'id': 'a', 'round': n} for n in (1, 2, 3, 4)]
    assert [r['round'] for r in up_to_round(rows, 3)] == [1, 2, 3]
    assert up_to_round(rows, None) == rows
