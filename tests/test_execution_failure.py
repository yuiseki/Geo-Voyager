import subprocess
from unittest.mock import patch

import pytest

from geo_voyager.target_ref import TargetRef
from geo_voyager.execution_failure import ExecutionFailure
from geo_voyager.intent import Intent
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.worker import Worker


@pytest.mark.parametrize('error', ['SyntaxError: invalid syntax', 'RuntimeError: failed'])
def test_generated_errors_are_bounded_failures(error):
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = subprocess.CalledProcessError(
            73, ['docker', 'run'], output='x' * 20000, stderr=error)
        result = Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('bad', '説明'))
    assert isinstance(result, ExecutionFailure)
    assert result.exit_code == 73 and error in result.stderr
    assert len(result.stdout) <= 8192


@pytest.mark.parametrize('code', [1, 125, 126, 127, 137])
def test_infrastructure_failure_propagates(code):
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.side_effect = subprocess.CalledProcessError(code, ['docker', 'run'], stderr='daemon failed')
        with pytest.raises(subprocess.CalledProcessError):
            Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('bad', '説明'))


def test_failure_redacts_secret_and_environment_dump():
    failure = ExecutionFailure.from_process(subprocess.CalledProcessError(
        73, [], output="TOKEN=private\nenviron({'HOME': '/x'})\nanswer", stderr='password: private'))
    assert 'private' not in failure.stdout + failure.stderr
    assert "'/x'" not in failure.stdout
    assert 'answer' in failure.stdout


def test_diagnostic_limit_is_utf8_bytes_not_characters():
    failure = ExecutionFailure.from_process(subprocess.CalledProcessError(73, [], stderr='失敗' * 10000))
    assert len(failure.stderr.encode('utf-8')) <= 8192


def test_parser_token_diagnostic_is_preserved_but_secret_assignments_are_not():
    failure = ExecutionFailure.from_process(subprocess.CalledProcessError(73, [], stderr='Unexpected token count\nAPI_KEY="private"\n{"HOME": "/hidden"}'))
    assert 'Unexpected token count' in failure.stderr
    assert 'private' not in failure.stderr and '/hidden' not in failure.stderr


def test_candidate_lines_are_renumbered_to_the_candidates_own_code():
    from geo_voyager.execution_failure import candidate_lines
    stderr = ('Traceback (most recent call last):\n  File "<stdin>", line 15, in <module>\n'
              '  File "<candidate>", line 7, in <module>\n  File "<candidate>", line 3, in helper\nKeyError: 0')
    fixed = candidate_lines(stderr, 2)
    assert 'File "<candidate>", line 5, in <module>' in fixed
    assert 'File "<candidate>", line 1, in helper' in fixed
    assert 'File "<stdin>", line 15' in fixed and fixed.endswith('KeyError: 0')


def test_a_frame_inside_the_injected_lines_is_left_alone():
    from geo_voyager.execution_failure import candidate_lines
    assert 'line 2,' in candidate_lines('  File "<candidate>", line 2, in <module>', 3)


def test_no_offset_changes_nothing():
    from geo_voyager.execution_failure import candidate_lines
    stderr = '  File "<candidate>", line 7, in <module>'
    assert candidate_lines(stderr, 0) == stderr


def test_a_real_traceback_points_the_failing_line_excerpt_at_the_right_statement():
    """Runs the sandbox wrapper on the host, with the same injected lines the Worker adds."""
    import subprocess
    import sys
    from geo_voyager.execution_attempt import ExecutionAttempt
    from geo_voyager.execution_failure import ExecutionFailure, candidate_lines, sandbox_program
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation
    from geo_voyager.repair_context import failing_line_excerpt
    from geo_voyager.worker import injected_lines

    candidate = 'import json\ndata = json.loads(previous_observations[0])\nname = data[0]\nprint(name)'
    intent = Intent('港区の件数', service_ids=('overpass',), target=TargetRef('港区'),
                    previous_observations=(Observation('{"name": "港区"}'),))
    prefix = injected_lines(intent)
    result = subprocess.run([sys.executable, '-I', '-B', '-'], input=sandbox_program(prefix + candidate),
                            capture_output=True, text=True)
    assert result.returncode == 73
    raw = ExecutionFailure('failed', result.stdout, result.stderr, result.returncode)
    # Unfixed, the line number is past the end of the candidate, so no excerpt can be made at all.
    assert failing_line_excerpt(candidate, raw) == ''
    fixed = ExecutionFailure('failed', result.stdout, candidate_lines(result.stderr, prefix.count('\n')), 73)
    excerpt = failing_line_excerpt(candidate, fixed)
    assert '>> 3: name = data[0]' in excerpt
