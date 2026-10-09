from bench.report import build_report, family


def step(**overrides):
    base = {'intent': 's', 'outcome_at': 0, 'candidate_attempts': 1, 'failure_types': [], 'oscillation': False,
            'critic_success': True, 'observation_head': '', 'services': ['taginfo'], 'datasets': [],
            'requires_context': False, 'reused_skill_failed': False, 'reused_skill_succeeded': False}
    base.update(overrides)
    return base


def row(id, correct, steps, **overrides):
    base = {'id': id, 'round': 1, 'correct': correct, 'goal_critic_success': correct, 'intents': steps,
            'required': ['taginfo'], 'target_relation': None, 'elapsed': 10.0}
    base.update(overrides)
    return base


def test_family_is_the_resource_kind_a_goal_needs():
    assert family({'required': ['overpass']}) == 'overpass'
    assert family({'required': ['yuiseki/jp-admin-2026-09']}) == 'dataset'
    assert family({'required': ['yuisekin-geosparql']}) == 'geosparql'
    assert family({'required': []}) == 'other'


def test_report_counts_correctness_categories_and_critic_errors():
    rows = [
        row('a', True, [step()]),
        row('b', False, [step(outcome_at=None, candidate_attempts=3, failure_types=['data_shape'] * 3,
                              critic_success=False)]),
        row('c', False, [step()], goal_critic_success=True),
        row('d', None, [step()]),
    ]
    report = build_report(rows)
    assert report['runs'] == 4 and report['correct'] == 1 and report['measured'] == 3
    assert report['categories'] == {'codegen': 1, 'semantic-completion': 1}
    assert report['unmeasured'] == 1
    assert report['critic']['false_positive'] == 1
    assert report['by_family']['taginfo'] == {'runs': 4, 'correct': 1, 'categories': {'codegen': 1, 'semantic-completion': 1}}


def test_report_has_planner_variance_per_goal_and_first_wrong_step():
    rows = [row('a', False, [step(), step(outcome_at=None, candidate_attempts=3, failure_types=['api_syntax'] * 3)]),
            row('a', True, [step()])]
    report = build_report(rows)
    assert report['planner']['a']['distinct_plans'] == 2
    assert report['first_wrong_step'] == {2: 1}


def test_report_success_at_k_over_candidate_chains():
    rows = [row('a', True, [step(outcome_at=1, candidate_attempts=2, failure_types=['syntax'])])]
    report = build_report(rows)
    assert report['success_at'] == {'0': 0.0, '1': 1.0, '2': 1.0}
