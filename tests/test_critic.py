from unittest.mock import Mock

import pytest

from geo_voyager.critic import Critic
from geo_voyager.critique import Critique
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation


def intent():
    return Intent('東京都23区で人口が最も多い区と人口を求める', ('yuiseki/jp-admin-2026-09',))


def test_no_observations_fails_without_llm():
    client = Mock()
    result = Critic(client).check(intent(), [])
    assert result.success is False and result.reason
    client.generate.assert_not_called()


@pytest.mark.parametrize('text', ['', ' ', '\n\t'])
def test_only_empty_observations_fails_without_llm(text):
    client = Mock()
    observation = Observation('temporary')
    observation.text = text
    result = Critic(client).check(intent(), [observation])
    assert result.success is False and result.reason
    client.generate.assert_not_called()


@pytest.mark.parametrize(('observation', 'reply', 'success'), [
    ('世田谷区、943664人', '判定: 成功\n理由: 区名と人口が回答されている', True),
    ('23区の人口データを取得した', '判定: 失敗\n理由: 人口最大の区名と人口が回答されていない', False),
])
def test_critic_uses_llm_to_check_intent_completion(observation, reply, success):
    client = Mock()
    client.generate.return_value = reply
    result = Critic(client).check(intent(), [Observation(observation)])
    assert result.success is success
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    assert intent().text in prompt and observation in prompt
    assert '仮説が正しいか、結果が望ましいかは判定しない' in prompt
    assert 'yuiseki/jp-admin-2026-09' not in prompt


def test_critic_passes_all_observation_texts():
    client = Mock()
    client.generate.return_value = '判定: 成功\n理由: 回答されている'
    Critic(client).check(intent(), [Observation('世田谷区'), Observation('943664人')])
    prompt = client.generate.call_args.args[0]
    assert '世田谷区' in prompt and '943664人' in prompt


def test_critic_rejects_malformed_llm_output():
    client = Mock()
    client.generate.return_value = 'おそらく成功です'
    with pytest.raises(ValueError):
        Critic(client).check(intent(), [Observation('世田谷区、943664人')])
