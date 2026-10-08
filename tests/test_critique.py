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
