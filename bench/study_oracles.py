"""Numbers study-geoai-algo-py reported in its experiment READMEs, used as oracles. Only the numbers are taken.

Each entry: the key a reference solution (and later a Goal's answer) reports, the reported value, and how far an
answer may be from it. Source: https://github.com/yuiseki/study-geoai-algo-py, src/<experiment>/README.md (Taito).
"""

ORACLES = {
    'G1': {
        'experiment': '001-B-logistic-regression',
        'checks': {
            'scenes_in_area': (53_948, 0),
            'rows_used': (32_593, 0),
            'undergrounded_share': (0.116, 0.001),
            'all_overhead_accuracy': (0.884, 0.001),
            'street_auc': (0.849, 0.01),
            'street_accuracy': (0.905, 0.01),
            'with_poles_and_wires_auc': (0.988, 0.01),
            'street_coefficients.lights_road': (-0.999, 0.02),
            'street_coefficients.green_ratio': (0.674, 0.02),
            'street_coefficients.roadway_width': (-0.421, 0.02),
            'street_coefficients.colorfulness': (0.144, 0.02),
            'street_coefficients.sidewalk_left': (-0.036, 0.02),
            'street_coefficients.sidewalk_right': (-0.009, 0.02),
            'poles_visible_coefficient': (-5.9, 0.1),
        },
    },
}


def compare(goal: str, answer: dict) -> list[dict]:
    """One row per check: the reported value, the answer's value, and whether it is within the tolerance."""
    rows = []
    for key, (expected, tolerance) in ORACLES[goal]['checks'].items():
        value = answer
        for part in key.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
        ok = isinstance(value, (int, float)) and abs(value - expected) <= tolerance + 1e-12
        rows.append({'key': key, 'expected': expected, 'tolerance': tolerance, 'answer': value, 'ok': ok})
    return rows
