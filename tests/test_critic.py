from unittest.mock import Mock

import pytest

from geo_voyager.target_ref import TargetRef
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


def test_critic_does_not_invent_missing_answers_from_external_knowledge():
    client = Mock()
    client.generate.return_value = '判定: 成功\n理由: 要求された名前一覧が回答されている'
    Critic(client).check(Intent('隣接する区域の名前を取得する', service_ids=('yuisekin-geosparql',)), [Observation('隣接する区域: 区域A、区域B')])
    assert '外部知識で答えを推測・追加しない' in client.generate.call_args.args[0]


def test_critic_does_not_assume_an_unspecified_expected_count():
    client = Mock()
    client.generate.return_value = '判定: 成功\n理由: 名前一覧を回答している'
    Critic(client).check(Intent('隣接する区域の名前を取得する', service_ids=('yuisekin-geosparql',)), [Observation('隣接する区域: 区域A、区域B')])
    assert 'Intent にない期待件数を仮定しない' in client.generate.call_args.args[0]


def test_critic_uses_zero_temperature_for_completion_judgement():
    client = Mock()
    client.generate.return_value = '判定: 成功\n理由: 回答されている'
    Critic(client).check(intent(), [Observation('世田谷区、943664人')])
    assert client.generate.call_args.kwargs['temperature'] == 0.0


def test_critic_receives_prior_observations_for_target_references():
    from unittest.mock import Mock
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation
    from geo_voyager.critic import Critic
    llm = Mock(); llm.generate.return_value = '判定: 成功\n理由: 対象に回答'
    intent = Intent('対象Bを測定', service_ids=('overpass',), target=TargetRef('対象B'),
                    previous_observations=(Observation('[{"name":"対象A"},{"name":"対象B"}]'),))
    Critic(llm).check(intent, [Observation('対象Bの件数は4')])
    assert '対象A' in llm.generate.call_args.args[0] and '対象B' in llm.generate.call_args.args[0]


def test_critic_context_does_not_refer_to_list_positions():
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: 対象が違う'
    intent = Intent('乙を測定', service_ids=('overpass',), target=TargetRef('乙'),
                    previous_observations=(Observation('[{"name":"甲"},{"name":"乙"}]'),))
    Critic(client).check(intent, [Observation('{"name":"甲","count":5}')])
    prompt = client.generate.call_args.args[0]
    assert 'N-1' not in prompt and '番目' not in prompt and 'previous_observations[0]' in prompt
    assert '名前と安定ID' in prompt


def test_critic_gets_the_target_resolved_by_name_wherever_it_is_in_the_list():
    for listing in ('[{"name":"甲","relation_id":"1"},{"name":"乙","relation_id":"2"}]',
                    '[{"name":"乙","relation_id":"2"},{"name":"甲","relation_id":"1"}]'):
        client = Mock(); client.generate.return_value = '判定: 成功\n理由: 対象が一致'
        intent = Intent('乙を測定', service_ids=('overpass',), target=TargetRef('乙'), previous_observations=(Observation(listing),))
        Critic(client).check(intent, [Observation('{"name":"乙","count":5}')])
        assert '解決済み参照対象: {"name": "乙", "id_type": "relation_id", "id_value": "2"}' in client.generate.call_args.args[0]


def test_critic_says_so_when_the_target_cannot_be_identified_uniquely():
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: 対象が不明'
    intent = Intent('丙を測定', service_ids=('overpass',), target=TargetRef('丙'),
                    previous_observations=(Observation('[{"name":"甲","relation_id":"1"}]'),))
    Critic(client).check(intent, [Observation('{"name":"甲","count":5}')])
    prompt = client.generate.call_args.args[0]
    assert '解決済み参照対象' not in prompt and '一意に特定できません' in prompt


def test_critic_states_the_target_of_the_intent_even_without_prior_observations():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: 対象が一致'
    Critic(client).check(Intent('渋谷区の ID を取得', service_ids=('overpass',), target=TargetRef('渋谷区')),
                         [Observation('{"name":"渋谷区","relation_id":"1759477"}')])
    assert 'Intent の対象: 渋谷区' in client.generate.call_args.args[0]


def test_critic_does_not_adopt_an_answer_present_only_in_prior_data():
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: 今回の回答が違う'
    Critic(client).check(Intent('前段から最大を求める', requires_context=True, previous_observations=(Observation('{"name":"乙","count":4}'),)), [Observation('{"name":"甲","count":0}')])
    assert '前段に正しい値があっても今回の回答が誤りなら失敗' in client.generate.call_args.args[0]


def test_default_critic_does_not_request_thinking():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: 回答がある'
    Critic(client).check(intent(), [Observation('{"count": 3}')])
    kwargs = client.generate.call_args.kwargs
    assert 'enable_thinking' not in kwargs and 'max_tokens' not in kwargs


def test_thinking_critic_enables_thinking_with_room_for_the_verdict():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: 回答がある'
    result = Critic(client, thinking=True).check(intent(), [Observation('{"count": 3}')])
    kwargs = client.generate.call_args.kwargs
    assert result.success
    assert kwargs['enable_thinking'] is True
    assert kwargs['max_tokens'] >= 2048 and kwargs['reasoning_budget_tokens'] > 0
    assert kwargs['temperature'] == 0.0


def test_the_prompt_does_not_accept_a_bare_zero_or_a_contradicting_value():
    from geo_voyager.critic import Critic
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation
    from unittest.mock import Mock
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: 根拠がない'
    Critic(client).check(Intent('cuisine=sushi の使用数を取得する', service_ids=('taginfo',)), [Observation('{"count": 0}')])
    prompt = client.generate.call_args.args[0]
    assert '0' in prompt and '空' in prompt and '矛盾' in prompt and '根拠が Observation に' in prompt


def _prompt(final):
    from geo_voyager.critic import Critic
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation
    from unittest.mock import Mock
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: x'
    Critic(client).check(Intent('渋谷区と新宿区のカフェ数を求め、どちらが多いかを示す', service_ids=('overpass',), requires_context=True),
                         [Observation('{"name": "渋谷区", "count": 459}'), Observation('{"name": "新宿区", "count": 343}')], final=final)
    return client.generate.call_args.args[0]


def test_the_final_check_wants_the_answer_itself_in_an_observation():
    prompt = _prompt(True)
    assert '最終判定' in prompt and '自分で比較・計算して答えを導かない' in prompt and '答えそのものを出力した Observation' in prompt


def test_a_step_check_does_not_carry_the_final_instruction():
    assert '最終判定' not in _prompt(False)


def _step_prompt(text):
    from geo_voyager.critic import Critic
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation
    from unittest.mock import Mock
    client = Mock(); client.generate.return_value = '判定: 失敗\n理由: x'
    Critic(client).check(Intent(text, service_ids=('overpass',), requires_context=True),
                         [Observation('{"cafe_count": 459, "restaurant_count": 1004}')])
    return client.generate.call_args.args[0]


def test_a_step_that_asks_for_a_comparison_wants_the_answer_itself():
    prompt = _step_prompt('cafe と restaurant の件数を比較し、どちらが多いかを示す')
    assert '比較の勝者' in prompt and '自分で比較・計算して答えを導かない' in prompt
    assert '最終判定' not in prompt
