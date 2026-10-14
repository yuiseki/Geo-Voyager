import pytest

from geo_voyager.critique import Critique


@pytest.mark.parametrize(('verdict', 'success'), [('成功', True), ('失敗', False)])
def test_parses_two_line_critique(verdict, success):
    assert Critique.from_text(f'判定: {verdict}\n理由: 要求された回答の有無') == Critique(
        success=success, reason='要求された回答の有無',
    )


@pytest.mark.parametrize('text', [
    '', '判定: 成功', '判定: 不明\n理由: 不明',
    '判定: 成功\n説明: 回答済み', '判定: 成功\n理由:   ',
    '理由: 回答済み\n判定: 成功', '判定: 成功\n理由: 回答済み\n追加の説明',
    '```\n判定: 成功\n理由: 回答済み\n```',
])
def test_rejects_invalid_format(text):
    with pytest.raises(ValueError):
        Critique.from_text(text)


def test_the_verdict_is_the_last_two_lines_after_the_checking_written_out():
    # Stage 5, case 29: the Critic wrote out its search of 57 pairs, first guessed 成功, found the pair missing and
    # ended on the two lines. Told to write the two lines only, it skipped the search and misread the list instead.
    reply = ('判定: 成功\n理由: 港区と目黒区の組も Observation に存在する\n待てよ、再確認する。\n'
             '- 港区の組: 中央区-港区、品川区-港区\n港区と目黒区の組はない。\n\n'
             '判定: 失敗\n理由: Intent が必ず含めるとした港区と目黒区の組が Observation に無い。')
    assert Critique.from_text(reply) == Critique(False, 'Intent が必ず含めるとした港区と目黒区の組が Observation に無い。')


@pytest.mark.parametrize('text', [
    '港区の組を数える。\n判定: 成功',                          # no reason after the verdict
    '判定: 成功\n理由: ok\n待てよ、再確認する。',                 # the checking goes on after the verdict
    '判定: 成功\n考えた。\n理由: ok',                            # the reason does not follow the verdict
])
def test_a_reply_that_does_not_end_on_the_two_lines_is_still_rejected(text):
    with pytest.raises(ValueError):
        Critique.from_text(text)
