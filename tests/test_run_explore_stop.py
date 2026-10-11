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
