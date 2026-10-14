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


def test_a_step_that_only_lists_things_is_not_told_to_want_a_selection():
    prompt = _step_prompt('台東区に境界が接する区の日本語名を求める')
    assert '比較の勝者' not in prompt


def test_the_critic_judges_values_not_the_key_names_an_intent_wrote():
    # Round 7: the Intent asked for cafe_count, the skill printed tag and count, and the step Critic rejected
    # the right counts. Over 44 stored rejections, saying so turned 15 right answers to success and no wrong one.
    from unittest.mock import Mock
    from geo_voyager.critic import Critic
    from geo_voyager.intent import Intent
    from geo_voyager.observation import Observation

    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    Critic(client).check(Intent('渋谷区の cafe の数を cafe_count で返す', service_ids=('overpass',)),
                         [Observation('{"name": "渋谷区", "tag": "amenity=cafe", "count": 459}')])
    prompt = client.generate.call_args.args[0]
    assert 'キー名の違いは失敗の理由にしない' in prompt
    assert prompt.index('キー名の違い') < prompt.index('Intent:\n')


def test_the_final_check_shows_each_observation_under_the_step_that_produced_it():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: x'
    goal = Intent('東京23区で ref の付いた駅が最も少ない区', service_ids=('overpass',), requires_context=True)
    observations = [Observation('[{"name": "江戸川区", "ref_count": 9}, {"name": "目黒区", "ref_count": 10}]'),
                    Observation('{"name": "江戸川区", "ref_count": 9}')]
    Critic(client).check(goal, observations, final=True, asked=('各区の ref の付いた駅数を測る', 'ref_count が最小の区を1件選ぶ'))
    prompt = client.generate.call_args.args[0]
    assert '- 調査項目: ref_count が最小の区を1件選ぶ\n  出力: {"name": "江戸川区", "ref_count": 9}' in prompt
    assert 'その調べ物の答えとして読む' in prompt


def test_the_steps_must_match_the_observations_one_to_one():
    with pytest.raises(ValueError):
        Critic(Mock()).check(intent(), [Observation('1'), Observation('2')], final=True, asked=('a',))


def test_without_the_steps_the_final_check_lists_the_observations_as_before():
    prompt = _prompt(True)
    assert '- {"name": "渋谷区", "count": 459}' in prompt and '調査項目:' not in prompt


def test_the_earlier_observations_are_cut_to_a_budget_so_the_prompt_fits_the_context():
    # Round 8, Goal 18: two earlier lists of 8 KB and 1.7 KB beside an 8 KB answer made a prompt of 8,456 tokens,
    # over the 8,192 of the context, and the server refused it (HTTP 400).
    from geo_voyager.critic import REFERENCE_BUDGET
    llm = Mock(); llm.generate.return_value = '判定: 成功\n理由: ok'
    pairs = Observation('[' + ', '.join('{"ward_a_name": "世田谷区", "ward_b_name": "大田区"}' for _ in range(160)) + ']')
    wards = Observation('[{"name": "千代田区", "relation_id": "1761742", "population": 67625}]')
    Critic(llm).check(Intent('区対の人口の合計', requires_context=True, previous_observations=(pairs, wards)), [Observation('{"total": 1}')])
    prompt = llm.generate.call_args.args[0]
    shown = prompt.split('前段 Observation', 1)[1]
    assert len(shown.encode('utf-8')) < REFERENCE_BUDGET + 1024
    assert '千代田区' in shown                                       # a short one is kept whole
    assert '以下略' in shown and f'全 {len(pairs.text.encode("utf-8"))} バイト' in shown


# Stage 4 (2026-10-14): 35 stored Critic calls judged by hand. Asked as they were, 28 were right. With the code that
# ran, the services and datasets it read, and the rule on facts of single places, 34: it saw that goal 4 counted the
# first ward only, stopped calling the right 57 pairs wrong for lacking 港区-目黒区 or holding 大田区-江戸川区, and read
# from the GeoSPARQL description that gs:Ward is the 23 wards.
SPARQL_COUNT = ('import json\nfrom geo_voyager.control_primitives import call_service\n\n\n'
                'def count_touching_pairs():\n    """Count."""\n'
                '    return json.loads(call_service("yuisekin-geosparql", path="/geo/sparql", params={"query": "q"}))\n')


def test_a_step_is_judged_with_the_code_that_ran_and_what_it_read():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: 件数がある'
    Critic(client).check(Intent('gs:Ward の sfTouches の区対を数える', service_ids=('yuisekin-geosparql',)),
                         [Observation('{"count": 57}')], code=SPARQL_COUNT)
    prompt = client.generate.call_args.args[0]
    assert 'この Observation を出力したコード' in prompt and 'count_touching_pairs' in prompt
    assert 'yuisekin-geosparql: YuisekinGeoSPARQLのpinned geographic graph。東京23区の全23個の gs:Ward' in prompt


def test_a_dataset_the_code_reads_by_its_argument_is_described_too():
    code = ('from geo_voyager.control_primitives import connect_duckdb, read_table\n\n\n'
            'def wards(dataset_id):\n    """Wards."""\n    with connect_duckdb() as connection:\n'
            '        return read_table(connection, dataset_id, "municipalities").count("*").fetchone()[0]\n')
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    Critic(client).check(intent(), [Observation('{"count": 23}')], code=code)
    assert 'yuiseki/jp-admin-2026-09: デジタル庁のアドレス・ベース・レジストリ' in client.generate.call_args.args[0]


def test_without_the_code_there_is_no_code_section():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    Critic(client).check(intent(), [Observation('世田谷区 943664')])
    assert 'この Observation を出力したコード' not in client.generate.call_args.args[0]


def test_facts_of_single_places_from_the_models_knowledge_are_no_reason_to_fail():
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    Critic(client).check(intent(), [Observation('世田谷区 943664')])
    prompt = client.generate.call_args.args[0]
    assert '個々の地物についての事実' in prompt and '値が 0 や空のこと、件数の桁が明らかに合わないことは疑ってよい' in prompt


def test_the_names_of_columns_to_read_and_values_carried_from_earlier_steps_are_no_reason_to_fail():
    # Goal 5, step 4: the Intent read rep_lon and rep_lat to output lon and lat, and the code carried each ward's
    # relation_id from the step before. The Critic rejected the right points for the column names and because the
    # dataset read has no relation_id, and the Goal lost two steps each run. It needed both sentences to accept.
    client = Mock(); client.generate.return_value = '判定: 成功\n理由: ok'
    Critic(client).check(intent(), [Observation('世田谷区 943664')])
    prompt = client.generate.call_args.args[0]
    names = prompt.index('読む元の列の名前が出力のキーに無いことを、失敗の理由にしない')
    carried = prompt.index('今回読んだデータやサービスがその種類の ID を持たないことを、失敗の理由にしない')
    assert prompt.index('キー名の違いは失敗の理由にしない') < names < carried < prompt.index('Intent:\n')
