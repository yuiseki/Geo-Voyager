import ast

from bench.goals import GOALS, judge_max, judge_strings, judge_winner, normalize_text
from bench.report import rejudge


def test_unicode_escapes_in_json_output_are_decoded_before_judging():
    escaped = '{"name": "\\u6749\\u4e26\\u533a", "relation_id": "1543055"}'
    assert '杉並区' in normalize_text(escaped)
    assert judge_max(escaped, {'name': '杉並区', 'count': 1543055})
    assert judge_strings('{"values": ["\\u7a1a\\u5185"]}', {'values': ['稚内']})


def test_plain_text_is_left_alone():
    assert normalize_text('世田谷区は943664人') == '世田谷区は943664人'
    assert normalize_text('path C:\\users\\name') == 'path C:\\users\\name'


def test_winner_judge_accepts_the_larger_side_named_with_its_count():
    oracle = {'counts': [8213, 24089]}
    labels = ('ramen', 'sushi')
    assert judge_winner('{"name": "cuisine=sushi", "count": 24089}', oracle, labels)
    assert judge_winner('sushi の方が多い（24,089 件）', oracle, labels)


def test_winner_judge_rejects_the_wrong_side_or_a_missing_count():
    oracle = {'counts': [8213, 24089]}
    labels = ('ramen', 'sushi')
    assert not judge_winner('{"name": "ramen", "count": 8213}', oracle, labels)
    assert not judge_winner('sushi の方が多い', oracle, labels)
    assert not judge_winner('{"type": "cafe", "count": 0}', {'counts': [459, 1004]}, ('cafe', 'restaurant'))


def test_every_goal_has_unique_id_a_parseable_oracle_and_required_resources():
    assert len({goal.id for goal in GOALS}) == len(GOALS)
    for goal in GOALS:
        ast.parse(goal.oracle_code)
        assert goal.required, goal.id


def test_rejudge_recomputes_correctness_from_the_recorded_final_observation():
    row = {'id': 'sparql_min_relation_ward', 'correct': False,
           'oracle': {'name': '杉並区', 'count': 1543055},
           'final_observation': '{"name": "\\u6749\\u4e26\\u533a", "relation_id": "1543055"}'}
    [fixed] = rejudge([row])
    assert fixed['correct'] is True and fixed['correct_recorded'] is False


def test_rejudge_keeps_rows_without_an_oracle_unmeasured():
    [row] = rejudge([{'id': 'cafe_shibuya', 'correct': None, 'final_observation': '{"count": 459}'}])
    assert row['correct'] is None


def test_a_ward_named_in_romaji_or_without_ku_is_the_same_winner():
    # Seen in a run: {"winner": "Shibuya", "count": 459}. The answer is right; only the language differs.
    oracle, labels = {'counts': [459, 343]}, ('渋谷区', '新宿区')
    for text in ('{"name": "Shibuya", "count": 459, "winner": "Shibuya"}', '{"winner": "shibuya-ku", "count": 459}',
                 '渋谷 の方が多い（459 件）'):
        assert judge_winner(text, oracle, labels), text
    assert not judge_winner('{"winner": "Shinjuku", "count": 459}', oracle, labels)
