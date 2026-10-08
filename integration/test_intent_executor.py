"""実embedding / LLM / Docker / Gatewayで既存再利用・学習・学習後の一致／言い換え再利用を確認。"""

import json
import math
import os
import re
import subprocess
import time
from dataclasses import asdict
from unittest.mock import Mock

import pytest

from geo_voyager.critic import Critic
from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from geo_voyager.worker import Worker
from integration.network_topology import network_topology
from integration.test_tokyo23_gateway import docker, gateway_code
from integration.test_worker_image import WORKER_IMAGE


def test_reuse_admin_and_station_then_learn_average_population(tmp_path):
    base_url = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base_url or not model:
        pytest.skip('Embedding endpoint and model must be explicitly configured')
    initial_skills = SkillLibrary().all()
    assert len(initial_skills) == 6
    library = SkillLibrary(tmp_path / 'skill_library')
    for skill in initial_skills:
        library.add(skill)
    # Spies delegate to real implementations; no LLM / HTTP / Docker responses are faked.
    library_spy = Mock(wraps=library)
    real_generator = SkillCandidateGenerator()
    generator = Mock(wraps=real_generator)

    def generate_logged(intent):
        candidate = real_generator.generate(intent)
        print('Candidate description:', candidate.description, flush=True)
        print('Candidate code:\n' + candidate.code, flush=True)
        (tmp_path / 'generated_candidate.py').write_text(candidate.code, encoding='utf-8')
        return candidate

    generator.generate.side_effect = generate_logged
    critic = Mock(wraps=Critic())
    reports = []
    with network_topology(isolated=True, gateway_code=gateway_code(include_stations=True),
                          worker_image=WORKER_IMAGE, include_origin=False) as names:
        docker('exec', names['gateway'], 'python', '-c', "from pathlib import Path; Path('/tmp/start').touch()")
        for _ in range(60):
            ready = subprocess.run(
                ['docker', 'exec', names['gateway'], 'python', '-c',
                 "import socket; socket.create_connection(('127.0.0.1',8000),timeout=1).close()"],
                capture_output=True, timeout=5,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        assert ready.returncode == 0, docker('logs', names['gateway'])
        worker_container = json.loads(docker('inspect', names['worker']))[0]
        assert set(worker_container['NetworkSettings']['Networks']) == {names['internal']}
        assert worker_container['Mounts'] == []
        worker = Mock(wraps=Worker(names['internal']))
        executor = IntentExecutor(
            SkillRetriever(library, EmbeddingClient(base_url, model)),
            SkillSelector(), worker, generator, critic, library_spy,
        )
        for text, dataset_id, expected in (
            ('東京都23区で人口が最も多い区と人口を求める', 'yuiseki/jp-admin-2026-09', '72c549dd-e449-4bef-97f1-e3a2eab27d64'),
            ('駅データに収録されている最北端の駅を求める', 'yuiseki/ekidata-jp', 'fb0fb79f-10b3-424f-ae27-4d6292f474c4'),
        ):
            intent = Intent(text, (dataset_id,))
            result = executor.execute(intent, k=4)
            assert str(result.selected_skill_id) == expected
            assert result.learned_skill_id is None and result.critique is None
            assert len(result.retrieved_skill_ids) == 4
            assert result.selected_skill_id in result.retrieved_skill_ids
            assert len(result.observations) == 1 and result.observations[0].text.strip()
            assert len(library.all()) == 6
            generator.generate.assert_not_called()
            critic.check.assert_not_called()
            library_spy.add.assert_not_called()
            report = {'intent': text, **asdict(result)}
            reports.append(report)
            print(json.dumps(report, ensure_ascii=False, default=str), flush=True)
        intent = Intent('東京都23区の平均人口を求める', ('yuiseki/jp-admin-2026-09',))
        result = executor.execute(intent, k=4)
        assert result.selected_skill_id is None
        assert result.learned_skill_id is not None
        assert result.critique is not None and result.critique.success
        assert len(result.retrieved_skill_ids) == 4
        assert len(library.all()) == 7
        generator.generate.assert_called_once_with(intent)
        critic.check.assert_called_once_with(intent, result.observations)
        library_spy.add.assert_called_once()
        worker.execute_skill.assert_called()
        assert worker.execute_skill.call_count == 2
        worker.execute_candidate.assert_called_once()
        learned = library.get(result.learned_skill_id)
        assert learned == library_spy.add.call_args.args[0]
        assert learned.id not in {skill.id for skill in initial_skills}
        assert 'load_admin_units' in learned.code
        assert 'aggregate(' in learned.code
        assert '13101' not in learned.code and '13123' not in learned.code
        assert 'https://' not in learned.code and 'http://' not in learned.code
        # Independently calculate the expected average from all 23 population values.
        reference_code = '''
from geo_voyager.control_primitives import connect_duckdb, load_admin_units
with connect_duckdb() as connection:
    rows = load_admin_units("yuiseki/jp-admin-2026-09", connection, area="東京都23区").fetchall()
    assert len(rows) == 23
    print(sum(row[2] for row in rows) / len(rows))
'''
        expected_average = float(DockerSandbox(image=WORKER_IMAGE, network=names['internal']).run(reference_code))
        numbers = [float(number) for number in re.findall(r'\d+(?:\.\d+)?', result.observations[0].text.replace(',', ''))]
        assert any(math.isclose(number, expected_average, abs_tol=1.0) for number in numbers)
        report = {'intent': intent.text, **asdict(result), 'phase': 'initial_learning', 'library_before': 6,
                  'generator_called': True, 'learned_description': learned.description,
                  'learned_code': learned.code, 'library_count': len(library.all())}
        reports.append(report)
        print(json.dumps(report, ensure_ascii=False, default=str), flush=True)
        # Reuse the exact learned Skill, then reuse it for a paraphrase in the same Library.
        for text in (
            intent.text,
            '東京都23区について、1区あたりの平均人口を計算して',
        ):
            reuse_intent = Intent(text, intent.dataset_ids)
            reused = executor.execute(reuse_intent, k=4)
            assert learned.id in reused.retrieved_skill_ids
            assert reused.selected_skill_id == learned.id
            assert reused.learned_skill_id is None and reused.critique is None
            assert reused.observations == result.observations
            assert len(library.all()) == 7
            # These counts must remain unchanged from the initial learning call.
            generator.generate.assert_called_once_with(intent)
            critic.check.assert_called_once_with(intent, result.observations)
            library_spy.add.assert_called_once()
            worker.execute_candidate.assert_called_once()
            report = {'intent': text, **asdict(reused), 'phase': 'learned_skill_reuse',
                      'generator_called': False, 'library_before': 7, 'library_count': len(library.all()),
                      'generator_call_count': generator.generate.call_count,
                      'save_call_count': library_spy.add.call_count}
            reports.append(report)
            print(json.dumps(report, ensure_ascii=False, default=str), flush=True)
        assert worker.execute_skill.call_count == 4
        logs = docker('logs', names['gateway'])
        assert 'GET 206 Range: bytes=' in logs
        assert '/datasets/yuiseki/ekidata-jp' in logs
        assert '/datasets/yuiseki/jp-admin-2026-09' in logs
    assert SkillLibrary().all() == initial_skills
    for role in ('worker', 'gateway'):
        assert names[role] not in docker('ps', '-a', '--format', '{{.Names}}')
    for role in ('internal', 'external'):
        assert names[role] not in docker('network', 'ls', '--format', '{{.Name}}')
    report_path = tmp_path / 'intent_execution.json'
    report_path.write_text(json.dumps(reports, ensure_ascii=False, default=str, indent=2) + '\n', encoding='utf-8')
    print('integration report:', report_path, flush=True)
    print('temporary Skill Library:', library.root, flush=True)
