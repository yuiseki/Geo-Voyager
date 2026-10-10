"""Reference solution of Goal G1, written by Claude Code to check that the analysis sandbox and the fixed data
reproduce the numbers study-geoai-algo-py reported for its experiment 001-B (Taito). Not shown to the Planner.

Rows: michiyomi scenes whose position (lat, lon) lies in Taito City, not quarantined, with the VLM's reading of
the overhead lines either 無電柱化済 (1) or 架空線あり (0), and no empty feature. Features, standardised:
roadway width, a sidewalk on the left and on the right (presence == あり), green ratio, colorfulness, road lights.
Scores are measured once on the out-of-fold predictions of a shuffled 5-fold split.
"""
import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from geo_voyager.analysis_primitives import connect_duckdb, data_path

STREET = ['roadway_width', 'sidewalk_left', 'sidewalk_right', 'green_ratio', 'colorfulness', 'lights_road']
LINES = ['poles_visible', 'wire_density_high']

con = connect_duckdb()
rows = con.sql(f"""
    with taito as (select geometry from '{data_path('jp-admin/municipalities.parquet')}' where code5 = '13106'),
    scenes as (
        select s.quarantined, s.green_ratio, s.colorfulness,
               json_extract_string(s.analysis, '$.infrastructure.utilities.undergrounded') as undergrounded,
               try_cast(json_extract(s.analysis, '$.geometry.roadway_width_m.value') as double) as roadway_width,
               json_extract_string(s.analysis, '$.geometry.sidewalk.left.presence') = 'あり' as sidewalk_left,
               json_extract_string(s.analysis, '$.geometry.sidewalk.right.presence') = 'あり' as sidewalk_right,
               try_cast(json_extract(s.analysis, '$.infrastructure.lighting.lights_road') as double) as lights_road,
               try_cast(json_extract(s.analysis, '$.infrastructure.utilities.poles_visible') as double) as poles_visible,
               json_extract_string(s.analysis, '$.infrastructure.utilities.wire_density') = '高' as wire_density_high
        from '{data_path('michiyomi/taito.parquet')}' s, taito
        where st_contains(taito.geometry, st_point(s.lon, s.lat))
    )
    select count(*) over () as scenes_in_area, *
    from scenes
""").fetchall()
names = ['scenes_in_area', 'quarantined', 'green_ratio', 'colorfulness', 'undergrounded', 'roadway_width',
         'sidewalk_left', 'sidewalk_right', 'lights_road', 'poles_visible', 'wire_density_high']
table = [dict(zip(names, row)) for row in rows]
scenes_in_area = table[0]['scenes_in_area']
used = [r for r in table if r['quarantined'] == 0 and r['undergrounded'] in ('無電柱化済', '架空線あり')
        and all(r[name] is not None for name in STREET + LINES)]

y = np.array([r['undergrounded'] == '無電柱化済' for r in used], dtype=int)
folds = KFold(n_splits=5, shuffle=True, random_state=0)


def scores(columns):
    x = np.array([[float(r[c]) for c in columns] for r in used])
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    probability = cross_val_predict(model, x, y, cv=folds, method='predict_proba')[:, 1]
    model.fit(x, y)
    coefficients = dict(zip(columns, (round(float(c), 3) for c in model[-1].coef_[0])))
    return roc_auc_score(y, probability), accuracy_score(y, probability >= 0.5), coefficients


street_auc, street_accuracy, street_coefficients = scores(STREET)
lines_auc, _, lines_coefficients = scores(STREET + LINES)
print(json.dumps({
    'scenes_in_area': scenes_in_area,
    'rows_used': len(used),
    'undergrounded_share': round(float(y.mean()), 4),
    'all_overhead_accuracy': round(float(1 - y.mean()), 4),
    'street_auc': round(street_auc, 4),
    'street_accuracy': round(street_accuracy, 4),
    'street_coefficients': street_coefficients,
    'with_poles_and_wires_auc': round(lines_auc, 4),
    'poles_visible_coefficient': lines_coefficients['poles_visible'],
}, ensure_ascii=False))
