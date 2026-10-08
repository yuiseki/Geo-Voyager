from unittest.mock import patch

from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.worker import Worker


def test_worker_returns_observations_through_docker_sandbox():
    intent = Intent("東京23区ごとのコンビニ件数を調べる", ("yuiseki/osm-japan-src-2026-08",))
    with patch("geo_voyager.worker.DockerSandbox") as sandbox:
        sandbox.return_value.run.return_value = "hello from sandbox\n"

        observations = Worker().execute(intent)

    sandbox.return_value.run.assert_called_once_with('print("hello from sandbox")')
    assert observations == [Observation("hello from sandbox")]
