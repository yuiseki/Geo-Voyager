import signal

import pytest

from bench.run_explore import STOP_FILE, exit_on_sigterm, stop_requested


def test_a_stop_file_in_the_output_directory_asks_to_stop_before_the_next_goal(tmp_path):
    assert not stop_requested(tmp_path)
    (tmp_path / STOP_FILE).write_text('')
    assert stop_requested(tmp_path)


def test_sigterm_exits_through_python_so_the_containers_are_removed():
    previous = signal.getsignal(signal.SIGTERM)
    try:
        exit_on_sigterm()
        with pytest.raises(SystemExit):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
    finally:
        signal.signal(signal.SIGTERM, previous)


from unittest.mock import patch
import subprocess

from bench.infra import environment_problem


def test_a_live_environment_has_no_problem():
    with patch('bench.infra.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '200\n', '')):
        assert environment_problem({'gateway': 'g'}) is None


def test_a_removed_gateway_or_geosparql_server_is_a_problem_named_in_the_message():
    # A cleanup removed the containers of a running exploration; every later step failed on name resolution and
    # the run went on recording failures as findings about the model.
    failed = subprocess.CompletedProcess([], 1, '', 'Error response from daemon: No such container: g')
    with patch('bench.infra.subprocess.run', return_value=failed):
        problem = environment_problem({'gateway': 'g'})
    assert problem and 'No such container' in problem
