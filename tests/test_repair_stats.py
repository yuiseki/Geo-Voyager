from geo_voyager.critique import Critique
from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent_execution import IntentExecution
from geo_voyager.observation import Observation
from geo_voyager.repair_stats import (
    classify_failure, error_line, intent_record, success_at, summarize,
)


def failure(stderr: str) -> ExecutionFailure:
    return ExecutionFailure('Generated Python execution failed', '', stderr, 73)


def failed(code: str, stderr: str) -> ExecutionAttempt:
    return ExecutionAttempt(code, [], failure(stderr))


def passed(code: str) -> ExecutionAttempt:
    return ExecutionAttempt(code, [Observation('{"ok": 1}')], None)


def execution(attempts, success=True, selected=None) -> IntentExecution:
    return IntentExecution(
        attempts[-1].observations, (), selected, None, Critique(success, 'r'), None,
        failure=attempts[-1].failure, attempts=tuple(attempts),
    )


def test_classify_syntax_error():
    assert classify_failure(failure(
        '  File "<candidate>", line 1\n    if :\n       ^\nSyntaxError: invalid syntax')) == 'syntax'


def test_classify_data_shape_errors():
    assert classify_failure(failure("AttributeError: 'list' object has no attribute 'get'")) == 'data_shape'
    assert classify_failure(failure('KeyError: "results"')) == 'data_shape'
    assert classify_failure(failure('TypeError: string indices must be integers')) == 'data_shape'
    assert classify_failure(failure('json.decoder.JSONDecodeError: Expecting value')) == 'data_shape'


def test_classify_assertion_on_count_is_observation_misread():
    assert classify_failure(failure('AssertionError: Expected 23 observations, got 24')) == 'assertion'


def test_classify_empty_result():
    assert classify_failure(failure('ValueError: No results found')) == 'empty_result'


def test_classify_http_400_is_api_syntax_even_when_the_body_is_html():
    stderr = ('Traceback (most recent call last):\n  File "<candidate>", line 6, in <module>\n'
              "RuntimeError: Service overpass HTTP 400: <?xml version=\"1.0\"?>\n<html>\n<body>\n"
              '<p>Error: line 1: parse error: Unknown query clause </p>\n[redacted]\n</body>\n</html>')
    assert classify_failure(failure(stderr)) == 'api_syntax'
    assert classify_failure(failure(
        'RuntimeError: Service yuisekin-geosparql HTTP 400: Parse error: Unresolved prefixed name: rdfs:label')) == 'api_syntax'


def test_classify_server_side_and_rate_errors_are_api_transient():
    assert classify_failure(failure('RuntimeError: Service overpass HTTP 429: busy')) == 'api_transient'
    assert classify_failure(failure('RuntimeError: Service overpass HTTP 504: gateway timeout')) == 'api_transient'
    assert classify_failure(failure('TimeoutError: timed out')) == 'api_transient'


def test_error_line_is_the_last_exception_line_not_the_last_line():
    stderr = 'Traceback:\nRuntimeError: Service x HTTP 400: bad\n</body>\n</html>'
    assert error_line(failure(stderr)) == 'RuntimeError: Service x HTTP 400: bad'
    assert error_line(failure('')) == ''


def test_classify_unknown_is_other():
    assert classify_failure(failure('ZeroDivisionError: division by zero')) == 'other'
    assert classify_failure(failure('')) == 'other'


def test_first_try_success_is_outcome_zero():
    record = intent_record('i', execution([passed('a')]))
    assert record['outcome_at'] == 0
    assert record['failure_types'] == []
    assert record['oscillation'] is False


def test_repair_success_records_attempt_index_and_failure_types():
    record = intent_record('i', execution([
        failed('a', 'SyntaxError: x'), passed('b')]))
    assert record['outcome_at'] == 1
    assert record['failure_types'] == ['syntax']


def test_exhausted_repairs_have_no_outcome():
    record = intent_record('i', execution([
        failed('a', 'KeyError: 1'), failed('b', 'KeyError: 2'), failed('c', 'KeyError: 3')], success=False))
    assert record['outcome_at'] is None
    assert record['failure_types'] == ['data_shape'] * 3


def test_oscillation_when_code_returns_to_an_earlier_attempt():
    record = intent_record('i', execution([
        failed('a', 'AssertionError: n'), failed('b', 'AttributeError: x'),
        failed('a', 'AssertionError: n')], success=False))
    assert record['oscillation'] is True


def test_no_oscillation_when_all_codes_differ():
    record = intent_record('i', execution([
        failed('a', 'KeyError: 1'), failed('b', 'KeyError: 2'), passed('c')]))
    assert record['oscillation'] is False


def test_selected_skill_attempt_is_not_counted_as_a_candidate_attempt():
    # The first attempt ran a reused skill and failed; the candidate chain starts after it.
    record = intent_record('i', execution([
        failed('skill', 'KeyError: 1'), passed('cand')], selected='some-id'))
    assert record['outcome_at'] == 0
    assert record['reused_skill_failed'] is True


def test_reused_skill_success_has_no_candidate_chain():
    record = intent_record('i', execution([passed('skill')], selected='some-id'))
    assert record['outcome_at'] is None
    assert record['candidate_attempts'] == 0
    assert record['reused_skill_succeeded'] is True


def test_output_is_one_json_row_with_code_hashes_not_code():
    record = intent_record('i', execution([failed('secret code', 'KeyError: 1'), passed('b')]))
    assert 'secret code' not in str(record)
    assert len(record['attempts'][0]['code_sha256']) == 64
    assert record['attempts'][0]['error_line'] == 'KeyError: 1'


def test_success_at_counts_cumulatively_over_candidate_chains():
    records = [
        {'candidate_attempts': 1, 'outcome_at': 0},
        {'candidate_attempts': 2, 'outcome_at': 1},
        {'candidate_attempts': 3, 'outcome_at': 2},
        {'candidate_attempts': 3, 'outcome_at': None},
    ]
    assert [success_at(records, k) for k in (0, 1, 2)] == [0.25, 0.5, 0.75]


def test_success_at_ignores_reused_skill_only_records():
    records = [{'candidate_attempts': 0, 'outcome_at': None}, {'candidate_attempts': 1, 'outcome_at': 0}]
    assert success_at(records, 0) == 1.0


def test_success_at_empty_is_none():
    assert success_at([], 0) is None


def test_summarize_counts_failure_types_and_oscillation():
    records = [
        {'candidate_attempts': 2, 'outcome_at': 1, 'failure_types': ['syntax'], 'oscillation': False},
        {'candidate_attempts': 3, 'outcome_at': None, 'failure_types': ['assertion', 'data_shape', 'assertion'], 'oscillation': True},
    ]
    summary = summarize(records)
    assert summary['intents'] == 2
    assert summary['success_at'] == {'0': 0.0, '1': 0.5, '2': 0.5}
    assert summary['failure_types'] == {'assertion': 2, 'data_shape': 1, 'syntax': 1}
    assert summary['oscillations'] == 1


def test_summarize_goals_reports_correctness_separately_from_critic():
    from geo_voyager.repair_stats import summarize_goals
    rows = [
        {'correct': True, 'goal_critic_success': True},
        {'correct': False, 'goal_critic_success': True},
        {'correct': False, 'goal_critic_success': False},
        {'correct': None, 'goal_critic_success': True},
    ]
    summary = summarize_goals(rows)
    assert summary['goals'] == 4
    assert summary['correct'] == 1
    assert summary['critic_success'] == 3
    # Critic said success but the oracle disagreed.
    assert summary['critic_false_positive'] == 1
    assert summary['oracle_missing'] == 1
