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


@pytest.mark.parametrize('code', [1, 125, 126, 127])
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


def test_output_over_the_limit_fails_instead_of_being_cut_silently():
    """56 pairs of wards with their names and populations printed 10 KB; cut at 8 KiB, the Critic read a list that
    stopped mid-object and could not tell why. Over the limit, the run fails and says what to change."""
    import subprocess
    import sys
    from geo_voyager.execution_failure import GENERATED_ERROR_EXIT, RESULT_LIMIT, sandbox_program

    result = subprocess.run([sys.executable, '-I', '-B', '-'], input=sandbox_program(f"print('x' * {RESULT_LIMIT + 100})"),
                            capture_output=True, text=True)
    assert result.returncode == GENERATED_ERROR_EXIT
    assert f'{RESULT_LIMIT + 101} bytes' in result.stderr
    assert '行か列を減らす' in result.stderr


def test_output_at_the_limit_is_kept():
    import subprocess
    import sys
    from geo_voyager.execution_failure import RESULT_LIMIT, sandbox_program

    result = subprocess.run([sys.executable, '-I', '-B', '-'], input=sandbox_program(f"print('x' * {RESULT_LIMIT - 1})"),
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert len(result.stdout.encode()) == RESULT_LIMIT


def test_a_table_of_the_countries_of_the_world_passes_to_the_next_step_while_a_diagnostic_stays_short():
    # The small tasks of GeoAI-skills (2026-10-14), task 17: the 217 countries' population (10.9 KB) and the
    # areas of Natural Earth's countries (26.7 KB) could not reach the next step under a limit of 8 KiB. The prompts
    # show an Observation cut to their budgets; the next step's code reads it whole.
    import subprocess
    import sys
    from geo_voyager.execution_failure import OUTPUT_LIMIT, RESULT_LIMIT, sandbox_program
    assert RESULT_LIMIT >= 512 * 1024 and OUTPUT_LIMIT == 8192          # 1,741 municipalities × 7 columns: 310 KB
    result = subprocess.run([sys.executable, '-I', '-B', '-'],
                            input=sandbox_program("import sys\nprint('x' * 30000)\nprint('e' * 20000, file=sys.stderr)"),
                            capture_output=True, text=True)
    assert result.returncode == 0 and len(result.stdout) == 30001 and len(result.stderr) <= OUTPUT_LIMIT


def test_code_killed_for_its_memory_is_a_failure_of_that_code():
    # GeoAI-skills' small task 11 (2026-10-15): code that read too much of the population grid was killed at the
    # sandbox's 1 GB (exit 137), and the whole Goal ended as an infrastructure error after 68 minutes.
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.profile.memory = '1g'
        sandbox.return_value.run.side_effect = subprocess.CalledProcessError(137, ['docker', 'run'], output='', stderr='')
        result = Worker('internal').execute_candidate(Intent('調査', ('admin',)), SkillCandidate('big', '説明'))
    assert isinstance(result, ExecutionFailure) and result.exit_code == 137
    assert 'MemoryError' in result.stderr and '1g' in result.stderr
