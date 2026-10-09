from geo_voyager.execution_attempt import ExecutionAttempt
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.repair_context import attempt_history_text, failing_line_excerpt

CODE = '\n'.join(f'line{n}' for n in range(1, 11))


def failure(stderr: str) -> ExecutionFailure:
    return ExecutionFailure('Generated Python execution failed', '', stderr, 73)


def attempt(code: str, stderr: str) -> ExecutionAttempt:
    return ExecutionAttempt(code, [], failure(stderr))


def test_excerpt_marks_the_failing_candidate_line_with_context():
    stderr = ('Traceback (most recent call last):\n  File "<stdin>", line 15, in <module>\n'
              '  File "<candidate>", line 7, in <module>\nKeyError: 0')
    excerpt = failing_line_excerpt(CODE, failure(stderr))
    assert '>> 7: line7' in excerpt
    assert '   5: line5' in excerpt and '   8: line8' in excerpt
    assert 'line3' not in excerpt and 'line10' not in excerpt


def test_excerpt_uses_the_innermost_candidate_frame():
    stderr = ('  File "<candidate>", line 2, in <module>\n'
              '  File "<candidate>", line 9, in helper\nValueError: x')
    assert '>> 9: line9' in failing_line_excerpt(CODE, failure(stderr))


def test_excerpt_is_empty_without_a_candidate_frame_or_with_a_bad_line_number():
    assert failing_line_excerpt(CODE, failure('SyntaxError: invalid syntax')) == ''
    assert failing_line_excerpt(CODE, failure('  File "<candidate>", line 99, in <module>\nKeyError: 0')) == ''


def test_history_lists_each_attempt_error_and_whether_the_code_changed():
    history = [
        attempt('a', 'KeyError: 0'),
        attempt('b', 'KeyError: 0'),
    ]
    text = attempt_history_text(history)
    assert '試行1: KeyError: 0' in text
    assert '試行2: KeyError: 0（直前の試行からコードは変わった）' in text


def test_history_says_when_the_code_is_identical_to_the_previous_attempt():
    text = attempt_history_text([attempt('a', 'KeyError: 0'), attempt('a', 'KeyError: 0')])
    assert '試行2: KeyError: 0（直前の試行とコードが同一）' in text


def test_history_warns_when_the_same_error_repeats():
    text = attempt_history_text([attempt('a', 'KeyError: 0'), attempt('b', 'KeyError: 0')])
    assert '同じエラーが繰り返されている' in text


def test_history_does_not_warn_for_a_different_error():
    text = attempt_history_text([attempt('a', 'KeyError: 0'), attempt('b', 'ValueError: x')])
    assert '同じエラーが繰り返されている' not in text


def test_history_flags_a_return_to_an_earlier_code_version():
    text = attempt_history_text([attempt('a', 'KeyError: 1'), attempt('b', 'KeyError: 2'), attempt('a', 'KeyError: 1')])
    assert '試行3: KeyError: 1（試行1とコードが同一）' in text


def test_empty_history_is_empty_text():
    assert attempt_history_text([]) == ''
