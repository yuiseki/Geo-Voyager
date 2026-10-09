import json

from bench.semantic_replay_stats import categorize, select_cases, summarize


def write_run(tmp_path, goal_id, round_, executions, row_extra=None):
    run = tmp_path / f'{goal_id}.r{round_}'
    run.mkdir()
    (run / 'goal_report.json').write_text(json.dumps({'intents': [e['intent'] for e in executions],
                                                      'executions': [e['execution'] for e in executions]}))
    return run


def step(code='print(1)', observation='{"count": 0}', critic=(False, 'too little'), failure=None, target=None):
    return {'intent': {'text': 't', 'dataset_ids': [], 'service_ids': ['overpass'], 'previous_observations': [],
                       'requires_context': False, 'target_name': target},
            'execution': {'observations': [{'text': observation}], 'critique': {'success': critic[0], 'reason': critic[1]},
                          'attempts': [{'code': code, 'observations': [{'text': observation}], 'failure': failure}]}}


def results_row(goal_id, round_, **extra):
    row = {'id': goal_id, 'round': round_, 'correct': False, 'goal_critic_success': False, 'required': ['overpass'],
           'target_relation': None, 'critic_thinking': False, 'oracle': {'count': 5}, 'final_observation': '{"count": 0}',
           'intents': [{'intent': 't', 'outcome_at': 0, 'candidate_attempts': 1, 'failure_types': [], 'oscillation': False,
                        'critic_success': False, 'observation_head': '{"count": 0}', 'services': ['overpass'], 'datasets': [],
                        'requires_context': False, 'reused_skill_failed': False, 'reused_skill_succeeded': False}]}
    row.update(extra)
    return row


def test_only_runs_the_critic_rejected_after_a_successful_execution_are_cases(tmp_path):
    write_run(tmp_path, 'cafe_shibuya', 1, [step()])
    accepted = results_row('library_setagaya', 1)
    accepted['intents'][0]['critic_success'] = True            # the Critic let a wrong answer through
    rows = [results_row('cafe_shibuya', 1), accepted]
    (tmp_path / 'results.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    write_run(tmp_path, 'library_setagaya', 1, [step(critic=(True, 'ok'))])
    cases, skipped = select_cases(tmp_path / 'results.jsonl')
    assert [c['goal_id'] for c in cases] == ['cafe_shibuya']
    assert skipped == {'the Critic accepted the wrong answer': 1}


def test_a_case_carries_the_candidate_observation_reason_and_history(tmp_path):
    write_run(tmp_path, 'cafe_shibuya', 1, [step(code='print(7)', observation='{"count": 0}', critic=(False, 'zero'), target='渋谷区')])
    (tmp_path / 'results.jsonl').write_text(json.dumps(results_row('cafe_shibuya', 1)))
    [case], _ = select_cases(tmp_path / 'results.jsonl')
    assert case['code'] == 'print(7)' and case['observations'] == ['{"count": 0}'] and case['reason'] == 'zero'
    assert case['intent']['target_name'] == '渋谷区' and case['step'] == 1 and case['history'] == ['print(7)']
    assert case['oracle'] == {'count': 5} and case['critic_thinking'] is False


def test_a_missing_goal_report_is_skipped_not_fatal(tmp_path):
    (tmp_path / 'results.jsonl').write_text(json.dumps(results_row('cafe_shibuya', 1)))
    cases, skipped = select_cases(tmp_path / 'results.jsonl')
    assert cases == [] and skipped == {'no goal report': 1}


def result(**overrides):
    base = {'status': 'proposed', 'executed': True, 'execution_failed': False, 'critic_success': False,
            'before': '{"count": 0}', 'after': '{"count": 1}', 'keys_removed': [], 'keys_added': []}
    base.update(overrides)
    return base


def test_categories_are_exclusive_and_ordered():
    assert categorize(result(critic_success=True)) == 'rescued'
    assert categorize(result()) == 'still_failing'
    assert categorize(result(status='unchanged', executed=False, after=None)) == 'unchanged'
    assert categorize(result(after='{"count": 0}')) == 'unchanged'            # code changed, output did not
    assert categorize(result(status='vibration', executed=False, after=None)) == 'vibration'
    assert categorize(result(status='hardcoded', executed=False, after=None)) == 'hardcoded_rejected'
    assert categorize(result(status='invalid', executed=False, after=None)) == 'invalid'
    assert categorize(result(execution_failed=True, after=None)) == 'worsened'
    assert categorize(result(after='')) == 'worsened'
    assert categorize(result(keys_removed=['name'])) == 'worsened'            # the output contract shrank


def test_a_rescue_that_changed_the_output_keys_is_still_a_rescue_and_is_counted_separately():
    summary = summarize([result(critic_success=True, keys_added=['count'])])
    assert summary['rescued'] == 1 and summary['output_keys_changed'] == 1


def test_summary_counts_every_case_once():
    results = [result(critic_success=True), result(), result(execution_failed=True, after=None),
               result(status='unchanged', executed=False, after=None)]
    summary = summarize(results)
    assert summary['cases'] == 4
    assert summary['rescued'] == 1 and summary['still_failing'] == 1 and summary['worsened'] == 1 and summary['unchanged'] == 1
    assert sum(summary[key] for key in ('rescued', 'still_failing', 'worsened', 'unchanged', 'vibration',
                                        'hardcoded_rejected', 'invalid')) == 4


def test_output_keys_of_an_object_and_of_a_list_of_objects():
    from bench.semantic_replay_stats import output_keys
    assert output_keys('{"name": "x", "count": 1}') == {'name', 'count'}
    assert output_keys('[{"name": "x", "relation_id": "1"}, {"name": "y", "uri": "u"}]') == {'name', 'relation_id', 'uri'}


def test_output_keys_are_none_when_there_is_no_object_shape():
    from bench.semantic_replay_stats import output_keys
    assert output_keys('plain text') is None and output_keys('[1, 2]') is None and output_keys('') is None


def test_refresh_keys_finds_a_removed_id_inside_a_list_of_objects():
    from bench.semantic_replay_stats import refresh_keys
    refreshed = refresh_keys(result(before='[{"name": "a", "relation_id": "1"}]',
                                    after='[{"name": "a", "relation_uri": "u"}]', critic_success=True))
    assert refreshed['keys_removed'] == ['relation_id'] and refreshed['keys_added'] == ['relation_uri']
    assert categorize(refreshed) == 'rescued'          # the Critic accepted it, the contract still changed
    assert summarize([refreshed])['output_keys_changed'] == 1


def test_refresh_keys_leaves_a_result_without_an_output_alone():
    from bench.semantic_replay_stats import refresh_keys
    assert refresh_keys(result(after=None, execution_failed=True))['keys_removed'] == []
