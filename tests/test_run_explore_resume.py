"""--resume takes up the Goals of an earlier run that stopped on the way, from their logs (candidate 1, stage 3)."""
from geo_voyager.critique import Critique
from geo_voyager.event_log import EventLog
from geo_voyager.goal_history import PlannerFailure

from bench.run_explore import still_to_replay, unfinished
from bench.run_goals import logged_llm


def log_of(out, number, goal, *, ended):
    log = EventLog(out / f'{number:03d}' / 'events.jsonl')
    log.start(goal, reason='理由')
    log.append(PlannerFailure('書式が違う', 'reply', 0))
    if ended:
        log.end('done', success=True)


def test_the_goals_without_an_end_are_found_in_their_order(tmp_path):
    log_of(tmp_path, 1, 'A', ended=True)
    log_of(tmp_path, 2, 'B', ended=False)
    log_of(tmp_path, 3, 'C', ended=False)
    (tmp_path / '004').mkdir()                         # the curriculum gave no Goal: nothing to take up
    found = unfinished(tmp_path)
    assert [(number, logged.goal, logged.reason) for number, logged in found] == [(2, 'B', '理由'), (3, 'C', '理由')]
    assert found[0][1].events == (PlannerFailure('書式が違う', 'reply', 0),)


def test_a_replay_into_the_same_directory_goes_on_after_the_goals_it_has_begun(tmp_path):
    log_of(tmp_path, 1, 'A', ended=True)
    log_of(tmp_path, 2, 'B', ended=False)
    assert still_to_replay(['A', 'B', 'C', 'D'], tmp_path) == ['C', 'D']
    assert still_to_replay(['A', 'B'], tmp_path / 'new') == ['A', 'B']


def test_the_model_calls_of_a_goal_taken_up_are_numbered_after_those_already_saved(tmp_path, monkeypatch):
    monkeypatch.setattr('bench.run_goals.LlamaClient', lambda: type('C', (), {'generate': lambda self, *a, **k: 'reply'})())
    for number in (1, 2):
        (tmp_path / f'llm_{number:02d}_prompt.txt').write_text('earlier')
    logged_llm(tmp_path).generate('later')
    assert (tmp_path / 'llm_01_prompt.txt').read_text() == 'earlier'
    assert (tmp_path / 'llm_03_prompt.txt').read_text() == 'later' and (tmp_path / 'llm_03_response.txt').read_text() == 'reply'
