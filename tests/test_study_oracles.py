from bench.study_oracles import ORACLES, compare


def test_an_answer_within_the_tolerance_passes_and_a_missing_key_fails():
    answer = {'scenes_in_area': 53_948, 'street_coefficients': {'lights_road': -0.99}, 'street_auc': 0.86}
    rows = {row['key']: row for row in compare('G1', answer)}
    assert rows['scenes_in_area']['ok'] and rows['street_coefficients.lights_road']['ok']
    assert rows['street_auc']['ok'] is False            # 0.011 away, beyond 0.01
    assert rows['rows_used']['ok'] is False and rows['rows_used']['answer'] is None


def test_every_oracle_names_its_experiment():
    assert all(entry['experiment'] and entry['checks'] for entry in ORACLES.values())
