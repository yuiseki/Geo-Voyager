"""4件の追加Skillを、実Docker / Gateway / Dataset / Criticで確認する。"""

import json
import math
import subprocess
import time

from geo_voyager.critic import Critic
from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill import SkillLibrary
from integration.network_topology import network_topology
from integration.test_tokyo23_gateway import docker, gateway_code
from integration.test_worker_image import WORKER_IMAGE


CASES = (
    ('東京都23区の人口合計を求める', 'yuiseki/jp-admin-2026-09', 'befbc141-baad-41bc-abdf-dc34311c3111'),
    ('東京都23区で人口が多い上位5区を求める', 'yuiseki/jp-admin-2026-09', 'f2d4785a-779a-4927-b75d-65d1e4852ab2'),
    ('駅データに収録されている駅の総数を求める', 'yuiseki/ekidata-jp', 'ccd6a22b-d795-4359-a06a-f2ac214e6a28'),
    ('駅データに収録されている最北端の駅を求める', 'yuiseki/ekidata-jp', 'fb0fb79f-10b3-424f-ae27-4d6292f474c4'),
)


def test_four_initial_skills_through_gateway_and_critic():
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
        library = SkillLibrary()
        sandbox = DockerSandbox(image=WORKER_IMAGE, network=names['internal'])
        results = []
        for text, dataset_id, skill_id in CASES:
            skill = library.get(skill_id)
            output = sandbox.run(f'dataset_id={dataset_id!r}\n' + skill.code).strip()
            assert output
            # Check the same calculation against the complete relation rather than hardcoded answers.
            if skill_id == CASES[0][2]:
                total = int(output.split('人口合計は')[1].split('人')[0])
                check = sandbox.run(f'''
dataset_id={dataset_id!r}
from geo_voyager.control_primitives import connect_duckdb, load_admin_units
with connect_duckdb() as connection:
    rows = load_admin_units(dataset_id, connection, area="東京都23区").fetchall()
    assert len(rows) == 23
    print(sum(row[2] for row in rows))
''')
                assert total == int(check)
            elif skill_id == CASES[1][2]:
                assert len(output.splitlines()) == 6
                populations = [int(line.split('人口')[1].split('人')[0]) for line in output.splitlines()[1:]]
                assert populations == sorted(populations, reverse=True)
            elif skill_id == CASES[2][2]:
                assert int(output.split('総数は')[1].split('件')[0]) > 0
            else:
                latitude = float(output.split('緯度は')[1].split('、')[0])
                longitude = float(output.split('経度は')[1].split('である')[0])
                assert math.isfinite(latitude) and -90 <= latitude <= 90
                assert math.isfinite(longitude) and -180 <= longitude <= 180
            intent = Intent(text, (dataset_id,))
            critique = Critic().check(intent, [Observation(output)])
            print(json.dumps({'skill_id': skill_id, 'observation': output,
                              'critic_success': critique.success, 'critic_reason': critique.reason},
                             ensure_ascii=False), flush=True)
            assert critique.success, critique.reason
            results.append(output)
        assert len(results) == 4
        worker = json.loads(docker('inspect', names['worker']))[0]
        assert set(worker['NetworkSettings']['Networks']) == {names['internal']}
        assert worker['Mounts'] == []
        logs = docker('logs', names['gateway'])
        assert '/datasets/yuiseki/ekidata-jp' in logs and '/datasets/yuiseki/jp-admin-2026-09' in logs
        assert 'GET 206 Range: bytes=' in logs
    for role in ('worker', 'gateway'):
        assert names[role] not in docker('ps', '-a', '--format', '{{.Names}}')
    for role in ('internal', 'external'):
        assert names[role] not in docker('network', 'ls', '--format', '{{.Name}}')
