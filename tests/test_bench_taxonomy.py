from bench.taxonomy import classify, plan_signature, planner_variance


def step(**overrides):
    base = {'intent': 's', 'outcome_at': 0, 'candidate_attempts': 1, 'failure_types': [],
            'critic_success': True, 'observation_head': '{"count": 1}', 'services': ['overpass'],
            'datasets': [], 'requires_context': False, 'reused_skill_failed': False}
    base.update(overrides)
    return base


def row(steps, **overrides):
    base = {'correct': False, 'goal_critic_success': False, 'intents': steps, 'required': ['overpass'],
            'target_relation': None}
    base.update(overrides)
    return base


def test_correct_rows_have_no_failure_category():
    assert classify(row([step()], correct=True)) is None


def test_unknown_oracle_is_unmeasured_not_a_failure_category():
    assert classify(row([step()], correct=None))['category'] == 'unmeasured'


def test_planning_exception_is_planning():
    result = classify(row([], error='ValueError: Plan must start with 調査項目:'))
    assert result['category'] == 'planning' and result['first_wrong_step'] is None


def test_plan_that_never_declares_a_required_resource_is_planning():
    result = classify(row([step(services=['yuisekin-geosparql'])], required=['overpass']))
    assert result['category'] == 'planning' and result['first_wrong_step'] == 1


def test_exhausted_syntax_or_shape_failures_are_codegen_at_that_step():
    steps = [step(), step(outcome_at=None, candidate_attempts=3, failure_types=['data_shape'] * 3, critic_success=False)]
    result = classify(row(steps))
    assert result['category'] == 'codegen' and result['first_wrong_step'] == 2


def test_exhausted_api_syntax_is_codegen_because_the_query_was_wrong():
    steps = [step(outcome_at=None, candidate_attempts=3, failure_types=['api_syntax'] * 3, critic_success=False)]
    assert classify(row(steps))['category'] == 'codegen'


def test_exhausted_with_only_transient_service_errors_is_execution():
    steps = [step(outcome_at=None, candidate_attempts=3, failure_types=['api_transient'] * 3, critic_success=False)]
    assert classify(row(steps))['category'] == 'execution'


def test_a_step_that_returns_another_target_is_retrieval_selection():
    steps = [step(observation_head='{"name": "世田谷区", "relation_id": "1759474"}', critic_success=False),
             step(observation_head='{"count": 56}')]
    result = classify(row(steps, target_relation=1761717))
    assert result['category'] == 'retrieval-selection' and result['first_wrong_step'] == 1


def test_selection_is_not_flagged_when_the_target_id_is_present():
    steps = [step(observation_head='{"name": "港区", "relation_id": "1761717"}'),
             step(observation_head='{"count": 22}')]
    result = classify(row(steps, target_relation=1761717, goal_critic_success=True))
    assert result['category'] == 'semantic-completion'  # everything looked fine, the answer was still wrong


def test_critic_failure_after_a_successful_run_is_semantic_completion():
    steps = [step(critic_success=False, observation_head='{"x": 1}')]
    result = classify(row(steps))
    assert result['category'] == 'semantic-completion' and result['first_wrong_step'] == 1


def test_critic_failure_of_the_last_local_aggregation_is_aggregation():
    steps = [step(), step(services=[], datasets=[], requires_context=True, critic_success=False)]
    result = classify(row(steps))
    assert result['category'] == 'aggregation' and result['first_wrong_step'] == 2


def test_exhausted_last_local_aggregation_is_still_codegen():
    steps = [step(), step(services=[], requires_context=True, outcome_at=None, candidate_attempts=3,
                          failure_types=['data_shape'] * 3, critic_success=False)]
    assert classify(row(steps))['category'] == 'codegen'


def test_all_steps_fine_but_wrong_answer_after_aggregation_is_aggregation():
    steps = [step(), step(services=[], requires_context=True)]
    assert classify(row(steps, goal_critic_success=True))['category'] == 'aggregation'


def test_reused_skill_steps_are_not_exhausted_chains():
    steps = [step(outcome_at=None, candidate_attempts=0, reused_skill_succeeded=True)]
    result = classify(row(steps, goal_critic_success=True))
    assert result['category'] == 'semantic-completion'


def test_plan_signature_lists_resources_per_step():
    steps = [step(services=['yuisekin-geosparql']), step(services=[], requires_context=True)]
    assert plan_signature(row(steps)) == (('yuisekin-geosparql',), ())


def test_planner_variance_counts_distinct_plans_and_the_modal_share():
    rows = [row([step()]), row([step()]), row([step(), step()]), row([step(services=['nominatim'])])]
    result = planner_variance(rows)
    assert result['runs'] == 4 and result['distinct_plans'] == 3
    assert result['step_counts'] == {1: 3, 2: 1}
    assert result['modal_share'] == 0.5
