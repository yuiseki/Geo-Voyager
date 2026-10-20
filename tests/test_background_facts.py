"""Background facts: what the loop is given to know before it explores, each checked on the data with the date and
how. A fact is shown when the text names one of its terms, so the prompts carry only the ones a Goal needs."""
from unittest.mock import Mock

from geo_voyager.background_facts import FACTS, facts_for
from geo_voyager.goal_history import GoalHistory
from geo_voyager.intent import Intent
from geo_voyager.planner import Planner
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator


def test_every_fact_says_how_and_when_it_was_checked():
    assert FACTS
    for fact in FACTS:
        assert fact['terms'] and fact['fact'] and fact['checked'] and fact['checked_on']


def test_a_fact_is_chosen_by_the_terms_the_text_names():
    texts = facts_for('東京23区境界内にある highway=footway の要素数は何件か')
    assert any('23 個の別々の' in text for text in texts)
    assert facts_for('札幌市の人口') == []


def test_the_planner_is_given_the_facts_its_goal_names():
    client = Mock(); client.generate.return_value = 'DONE'
    Planner(client).next('東京23区境界内にある highway=footway の要素数は何件か', GoalHistory())
    prompt = client.generate.call_args.args[0]
    assert '前提知識' in prompt and '23 個の別々の' in prompt
    client.generate.reset_mock()
    Planner(client).next('札幌市の人口', GoalHistory())
    assert '前提知識' not in client.generate.call_args.args[0]


def test_the_generator_is_given_the_facts_its_intent_names():
    client = Mock(); client.generate.return_value = '説明:\nx\n---\nコード:\n```python\ndef f():\n    """x"""\n    return 1\n```'
    try:
        SkillCandidateGenerator(client).generate(Intent('東京駅の座標を取得する', ('yuiseki/ekidata-jp',)))
    except Exception:
        pass
    assert "station_name = '東京'" in client.generate.call_args.args[0]


def test_the_critic_is_given_the_facts_its_intent_or_observations_name():
    # Explore 41: 双葉町 had no one in the 2020 census, and the Critic failed the answer 0 as unrealistic, in two Goals;
    # one of them named the town only in the Observation.
    from geo_voyager.critic import Critic
    from geo_voyager.observation import Observation
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: x'
    Critic(client).check(Intent('運行中駅を持つ市区町村のうち人口が最小のもの', ('yuiseki/jp-admin-2026-09',)), [Observation('{"name": "双葉町", "population": 0}')])
    assert '双葉町' in client.generate.call_args.args[0] and '前提知識' in client.generate.call_args.args[0]
    Critic(client).check(Intent('札幌市の人口', ('yuiseki/jp-admin-2026-09',)), [Observation('{"population": 1973395}')])
    assert '前提知識' not in client.generate.call_args.args[0]
