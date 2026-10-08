from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.worker import Worker


def test_worker_returns_observations_for_intent():
    intent = Intent("東京23区ごとのコンビニ件数を調べる", "yuiseki/osm-japan-src-2026-08")

    observations = Worker().execute(intent)

    assert isinstance(observations, list)
    assert len(observations) >= 1
    assert all(isinstance(observation, Observation) for observation in observations)
    assert all(observation.text for observation in observations)
