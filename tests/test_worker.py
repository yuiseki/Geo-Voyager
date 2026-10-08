from unittest.mock import patch

import pytest

from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.worker import Worker


def test_worker_reads_intent_dataset_through_internal_docker_sandbox():
    intent = Intent('東京都23区で人口が最も多い区と人口を求める', ('yuiseki/jp-admin-2026-09',))
    text = '東京都23区で人口が最も多い区は世田谷区で、人口は943664人である'
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        sandbox.return_value.run.return_value = text + '\n'
        observations = Worker(network='test-internal').execute(intent)
    sandbox.assert_called_once_with(image='geo-voyager-worker:duckdb-1.5.6', network='test-internal')
    code = sandbox.return_value.run.call_args.args[0]
    assert 'yuiseki/jp-admin-2026-09' in code
    assert 'most_populous_ward' in code
    assert observations == [Observation(text)]


def test_worker_rejects_unsupported_intent_dataset_before_docker():
    with patch('geo_voyager.worker.DockerSandbox') as sandbox:
        with pytest.raises(ValueError, match='dataset'):
            Worker(network='test-internal').execute(Intent('人口最大の区', ('unknown/dataset',)))
    sandbox.return_value.run.assert_not_called()
