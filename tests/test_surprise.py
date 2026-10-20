"""How far the answer of a Goal was from what the curriculum predicted: the reward that gives it curiosity.

0 is a prediction that came true; 1 is one wrong by a factor of ten or more, or a name the answer does not have.
"""
import pytest

from geo_voyager.surprise import surprise


def test_a_number_that_came_true_is_no_surprise():
    assert surprise('3777491', '{"name": "横浜市", "population": 3777491}') == 0


def test_a_number_wrong_by_a_factor_is_the_size_of_that_factor_in_tens():
    assert surprise('約 200 万人', '{"name": "横浜市", "population": 3777491}') == pytest.approx(0.276, abs=0.001)
    assert surprise('370万人', '{"population": 3777491}') == pytest.approx(0.009, abs=0.001)
    assert surprise('1.5億', '{"population": 126146099}') == pytest.approx(0.075, abs=0.001)


def test_wrong_by_ten_times_or_more_is_the_whole_surprise():
    assert surprise('10', '{"count": 103484}') == 1
    assert surprise('100000', '{"count": 3}') == 1


def test_the_number_of_the_answer_nearest_the_prediction_is_the_one_compared():
    # The answer has several numbers; which one the prediction meant is not known, so the least surprise is taken.
    assert surprise('25', '{"pref": "高知県", "stations": 165, "value": 23.86}') == pytest.approx(0.020, abs=0.001)


def test_a_number_written_as_text_in_the_answer_counts():
    assert surprise('24', '{"prefecture_name": "高知県", "value": "23.860"}') < 0.01


def test_a_name_the_answer_has_is_no_surprise_and_one_it_has_not_is_the_whole():
    assert surprise('横浜市', '{"code5": "14100", "name": "横浜市", "population": 3777491}') == 0
    assert surprise('大阪市', '{"code5": "14100", "name": "横浜市", "population": 3777491}') == 1
    assert surprise('「中央アフリカ共和国」', '{"country_code": "CAF", "name_ja": "中央アフリカ共和国"}') == 0


def test_a_zero_or_a_sign_that_differs_is_the_whole_surprise_unless_both_are_zero():
    assert surprise('0', '{"count": 0}') == 0
    assert surprise('0', '{"count": 12}') == 1
    assert surprise('-3', '{"change": 4}') == 1


def test_nothing_to_compare_is_no_reward_at_all():
    assert surprise('', '{"count": 3}') is None
    assert surprise('12', '{"name": "横浜市"}') is None


def test_a_name_the_answer_writes_shorter_at_its_end_is_no_surprise():
    # Explore 19: the prediction 横浜市営地下鉄ブルーライン was counted the whole surprise for an answer that wrote
    # ブルーライン. A name that ends the prediction is the same name, written shorter; one that begins it is not.
    assert surprise('横浜市営地下鉄ブルーライン', '{"station_name": "新横浜", "line_names": ["JR横浜線", "ブルーライン"]}') == 0
    assert surprise('横浜市港北区', '{"name": "港北区", "population": 358530}') == 0
    assert surprise('東京都千代田区', '{"pref": "東京都", "name": "中央区"}') == 1
    assert surprise('世田谷区', '{"name": "区"}') == 1


def test_a_station_predicted_with_eki_is_the_station_the_data_names_without_it():
    # Explore 37: the prediction 新宿駅 was counted the whole surprise for 新宿, as ekidata-jp and OSM name the station.
    assert surprise('新宿駅', '{"stations": [{"station_g_cd": 1130208, "station_name": "新宿", "line_count": 13}]}') == 0
    assert surprise('新宿駅', '{"station_name": "渋谷"}') == 1
