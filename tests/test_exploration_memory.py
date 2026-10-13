"""The record of an earlier exploration of the same Goal, given to the Planner (an Exploration Graph of one edge:
what was tried, how it failed). The experiment changes only whether the Planner is given it."""
from unittest.mock import Mock

from bench.exploration_memory import memory_of
from geo_voyager.goal_history import GoalHistory
from geo_voyager.planner import Planner

TRACE = {'goal': 'G', 'events': [
    {'kind': 'step', 'step': 1, 'intent': '駅を数える', 'succeeded': False, 'failure': '', 'critic_reason': '根拠が無い',
     'observation': '{"count": 458}', 'attempts': 1},
    {'kind': 'planner_failure', 'reason': 'ValueError: 対象が実体でない', 'reply': 'x', 'after_step': 1},
    {'kind': 'step', 'step': 2, 'intent': '駅を区ごとに数える', 'succeeded': False, 'failure': 'KeyError: name',
     'critic_reason': '', 'observation': '', 'attempts': 3},
    {'kind': 'step', 'step': 3, 'intent': '区の一覧', 'succeeded': True, 'failure': '', 'critic_reason': 'ok',
     'observation': '[1, 2]', 'attempts': 1},
    {'kind': 'final_critic_failure', 'reason': '答えが無い', 'after_step': 3}]}


def test_the_memory_says_each_step_how_it_ended_and_why():
    text = memory_of(TRACE, 'max_steps')
    assert '止まり方: max_steps' in text
    assert '駅を数える' in text and 'Critic が棄却' in text and '根拠が無い' in text and '{"count": 458}' in text
    assert '駅を区ごとに数える' in text and '実行の失敗' in text and 'KeyError: name' in text
    assert '区の一覧' in text and '成功' in text
    assert '計画の失敗: ValueError: 対象が実体でない' in text and '最終判定の失敗: 答えが無い' in text


def test_the_memory_is_bounded():
    long = {'goal': 'G', 'events': [dict(TRACE['events'][0], step=n, critic_reason='理' * 500) for n in range(1, 30)]}
    assert len(memory_of(long, 'max_steps')) <= 2500


def test_the_planner_is_shown_the_memory_only_when_given_one():
    client = Mock(); client.generate.return_value = 'DONE'
    Planner(client).next('G', GoalHistory())
    assert '前回この Goal を探索したときの記録' not in client.generate.call_args.args[0]
    Planner(client).next('G', GoalHistory(), memory='前回の記録の本文')
    prompt = client.generate.call_args.args[0]
    assert '前回この Goal を探索したときの記録' in prompt and '前回の記録の本文' in prompt


def test_the_executor_passes_the_memory_to_every_call_of_the_planner():
    from geo_voyager.goal_executor import GoalExecutor
    from geo_voyager.planner import DONE
    from geo_voyager.critique import Critique
    planner = Mock(); planner.next.return_value = DONE
    critic = Mock(); critic.check.return_value = Critique(True, 'ok')
    GoalExecutor(planner, Mock(), critic).execute_adaptive('G', memory='M')
    assert planner.next.call_args.kwargs['memory'] == 'M'


def test_the_memories_are_those_of_the_goals_an_earlier_run_did_not_answer(tmp_path):
    import json
    from bench.exploration_memory import memories_from
    rows = [{'number': 1, 'goal': 'A', 'success': True, 'stop_reason': 'done'},
            {'number': 2, 'goal': 'B', 'success': False, 'stop_reason': 'max_steps'},
            {'number': 3, 'goal': 'C', 'success': False, 'stop_reason': 'error'}]
    (tmp_path / 'exploration.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in rows))
    (tmp_path / '002').mkdir()
    (tmp_path / '002' / 'trace.json').write_text(json.dumps(TRACE))
    memories = memories_from(tmp_path)
    assert list(memories) == ['B'] and '止まり方: max_steps' in memories['B']        # C left no trace
