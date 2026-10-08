"""実 LLM 生成 → sandbox → Critic → 隔離した filesystem Library の明示確認。"""

import ast
import subprocess
import time

from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.worker import Worker
from integration.network_topology import network_topology
from integration.test_tokyo23_gateway import docker, gateway_code
from integration.test_worker_image import WORKER_IMAGE


def test_generated_least_populous_ward_skill(tmp_path):
    intent = Intent(
        text='東京都23区で人口が最も少ない区と人口を求める',
        dataset_ids=('yuiseki/jp-admin-2026-09',),
    )
    candidate = SkillCandidateGenerator().generate(intent)
    print('description:', candidate.description, flush=True)
    print('code:\n' + candidate.code, flush=True)
    assert 'load_admin_units' in candidate.code
    tree = ast.parse(candidate.code)
    assert not any(isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                   and node.id == 'dataset_id' for node in ast.walk(tree))
    assert 'https://' not in candidate.code and 'http://' not in candidate.code
    library = SkillLibrary(tmp_path)
    assert library.all() == []
    with network_topology(isolated=True, gateway_code=gateway_code(),
                          worker_image=WORKER_IMAGE, include_origin=False) as names:
        docker('exec', names['gateway'], 'python', '-c', "from pathlib import Path; Path('/tmp/start').touch()")
        for attempt in range(60):
            ready = subprocess.run(
                ['docker', 'exec', names['gateway'], 'python', '-c',
                 "import socket; socket.create_connection(('127.0.0.1',8000),timeout=1).close()"],
                capture_output=True, timeout=5,
            )
            if ready.returncode == 0:
                break
            time.sleep(0.25)
        assert ready.returncode == 0, docker('logs', names['gateway'])
        observations, critique = Worker(network=names['internal']).execute_candidate(
            intent, candidate, Critic(), library,
        )
        assert len(observations) == 1
        assert '千代田区' in observations[0].text
        assert '66680' in observations[0].text.replace(',', '')
        assert critique.success is True
        skills = library.all()
        assert len(skills) == 1
        skill = skills[0]
        assert skill.code == candidate.code and skill.description == candidate.description
        assert 'GET 206 Range: bytes=' in docker('logs', names['gateway'])
        print('Observation:', observations[0].text, flush=True)
        print('Critic:', critique, flush=True)
        print('Skill UUID:', skill.id, flush=True)
        print('Skill Library:', library.root, flush=True)
    for role in ('worker', 'gateway'):
        assert names[role] not in docker('ps', '-a', '--format', '{{.Names}}')
    for role in ('internal', 'external'):
        assert names[role] not in docker('network', 'ls', '--format', '{{.Name}}')
