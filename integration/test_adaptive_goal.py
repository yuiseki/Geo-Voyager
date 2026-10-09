"""Focused real-LLM check of the step-by-step route. Skipped unless the embedding endpoint is configured.

The LLM is not deterministic, so this asserts what the route has to guarantee, not an exact plan: a target an
earlier step made known is known to the Planner at a later step, and the Goal reaches DONE with an answer the
independent oracle agrees with. It is flaky: in a few runs of the committed code it passed in about half of
them, and in four runs of the commit before the replanning change it passed in three.
"""
import os

import pytest

from bench.infra import benchmark_environment
from bench.run_adaptive import run_one
from geo_voyager.embedding_client import EmbeddingClient


def test_a_target_made_known_in_one_step_is_used_in_the_next_and_the_goal_reaches_done(tmp_path):
    base, model = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL'), os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base or not model:
        pytest.skip('Configure the local embedding endpoint explicitly')
    with benchmark_environment() as names:
        row = run_one('hospital_minato', names, tmp_path / 'run', EmbeddingClient(base, model))
    steps = row['steps']
    assert row['stop_reason'] == 'done' and row['critique']['success'], row['critique']
    first = next(index for index, step in enumerate(steps) if step['new_targets'])
    # Nominatim names a target by its display name, for example '港区, 東京都, 日本'.
    assert any('港区' in target['name'] for target in steps[first]['new_targets'])
    assert any(step['known_before'] for step in steps[first + 1:]), 'a later step must start knowing the target'
    assert row['correct'] is True, (row['final_observation'], row['oracle'])
