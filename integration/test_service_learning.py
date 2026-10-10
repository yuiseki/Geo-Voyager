"""Real service discovery, candidate learning and reuse; explicit integration only."""
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.critic import Critic
from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.llama_client import LlamaClient
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.worker import Worker
from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_tokyo23_gateway import docker
from integration.test_worker_image import WORKER_IMAGE


@contextmanager
def pinned_geosparql(names):
    repo = Path(__file__).resolve().parents[2] / 'YuisekinGeoSPARQL'
    manifest = json.loads((repo / 'data/manifest.json').read_text())
    config = (repo / 'fuseki/config-head.ttl').read_text().replace('geo:indexEnabled    true ;', 'geo:indexEnabled    true ;\n    geo:srsUri <http://www.opengis.net/def/crs/OGC/1.3/CRS84> ;\n    geo:spatialIndexFile \"/tmp/spatial.index\" ;')
    for source in manifest['sources']:
        file = source['ttl_file']
        assert Path(file).name == file
        assert hashlib.sha256((repo / 'data' / file).read_bytes()).hexdigest() == source['ttl_sha256']
        config += f'    ja:data <file:///data/{file}> ;\n'
    config += '.\n[] a fuseki:Server ; ja:context [ ja:cxtName "arq:httpServiceAllowed" ; ja:cxtValue "false" ] .\n'
    network = 'geo-sparql-isolated-' + uuid4().hex
    container = network + '-server'
    try:
        docker('network', 'create', '--internal', '--opt',
               'com.docker.network.bridge.gateway_mode_ipv4=isolated', network)
        docker('network', 'connect', network, names['gateway'])
        command = "printf %s " + shlex.quote(config) + " > /tmp/config.ttl; exec java -Xmx1024m -Djava.io.tmpdir=/tmp -jar /fuseki/fuseki-server.jar --config=/tmp/config.ttl --port=3030"
        docker('run', '--detach', '--name', container, '--network', network,
               '--network-alias', 'geosparql', '--user', '65534:65534', '--read-only',
               '--tmpfs', '/tmp:rw,nosuid,size=128m', '--cap-drop', 'ALL',
               '--security-opt', 'no-new-privileges', '--memory', '2g', '--cpus', '2',
               '--pids-limit', '128', '--mount', f'type=bind,source={repo / "data"},target=/data,readonly',
               '--env', 'FUSEKI_BASE=/tmp/fuseki', '--entrypoint', 'sh', 'geo-voyager-geosparql:jena-6.2.0', '-c', command)
        for _ in range(60):
            ready = subprocess.run(['docker', 'exec', names['gateway'], 'python', '-c',
                "from urllib.request import urlopen; print(urlopen('http://geosparql:3030/geo/sparql?query=ASK%7B%7D',timeout=2).status)"],
                capture_output=True, timeout=5)
            if ready.returncode == 0:
                break
            time.sleep(0.5)
        assert ready.returncode == 0, docker('logs', container)
        info = json.loads(docker('inspect', container))[0]
        assert set(info['NetworkSettings']['Networks']) == {network}
        ip = info['NetworkSettings']['Networks'][network]['IPAddress']
        direct = DockerSandbox(image=WORKER_IMAGE, network=names['internal']).run(
            f"import socket\ntry:\n socket.create_connection(({ip!r},3030),timeout=2)\nexcept OSError:\n print('GeoSPARQL direct access blocked')\nelse:\n raise AssertionError('direct access allowed')")
        assert 'blocked' in direct
        yield manifest
    finally:
        docker('rm', '--force', container)
        docker('network', 'disconnect', network, names['gateway'])
        docker('network', 'rm', network)


@pytest.mark.parametrize('case,text,service_ids', [
    ('taginfo_overpass', 'OSMで火山をどう表現するかTaginfoで調べ、返答のkeyとvalueを両方使って日本の国境内の火山をOverpassで取得する。発見したタグと取得した火山の名前を回答する。', ('taginfo', 'overpass', 'nominatim')),
    ('nominatim', '上野駅の位置（緯度・経度）とOSM objectの種類・IDを取得する', ('nominatim',)),
    ('geosparql', 'YuisekinGeoSPARQLのpinned graphで台東区に境界が接する区の日本語名を求める。', ('yuisekin-geosparql',)),
])
def test_unknown_service_skill_is_learned_then_reused(tmp_path, case, text, service_ids):
    base = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base or not model:
        pytest.skip('Configure real embedding endpoint and model explicitly')
    (tmp_path / 'skill_library').mkdir()
    library = SkillLibrary(tmp_path / 'skill_library')
    library_spy = Mock(wraps=library)
    llm = Mock(wraps=LlamaClient())
    real_llm_generate = llm.generate._mock_wraps
    def generate_response_logged(*args, **kwargs):
        text = real_llm_generate(*args, **kwargs)
        (tmp_path / 'llm_response.txt').write_text(text)
        return text
    llm.generate.side_effect = generate_response_logged
    generator = Mock(wraps=SkillCandidateGenerator(llm))
    real_generate = generator.generate._mock_wraps
    def generate_logged(intent, skills=()):
        candidate = real_generate(intent, skills)
        print('DESCRIPTION:', candidate.description, flush=True)
        print('CODE:\n' + candidate.code, flush=True)
        (tmp_path / 'candidate.py').write_text(candidate.code)
        return candidate
    generator.generate.side_effect = generate_logged
    intent = Intent(text, service_ids=service_ids)
    with network_topology(isolated=True, gateway_code=gateway_code(), worker_image=WORKER_IMAGE,
                          include_origin=False) as names:
        wait_for_gateway(names['gateway'])
        with pinned_geosparql(names) as manifest:
            retriever = SkillRetriever(library, EmbeddingClient(base, model))
            critic = Mock(wraps=Critic())
            executor = IntentExecutor(retriever, Worker(names['internal']),
                                      generator, critic, library_spy)
            try:
                first = executor.execute(intent, k=4)
                print('FIRST:', json.dumps(asdict(first), ensure_ascii=False, default=str), flush=True)
                # The first run saves its function as a Skill. The same Intent again (rare in use: the adaptive loop
                # stops a repeated Intent) must still succeed, and the saved Skill must be retrieved for it. Whether it is
                # called is not required: the model may write a new function, as Voyager's agent may.
                assert first.critique.success and first.learned_skill is not None and len(library.all()) == 1
                name = first.learned_skill.split('@')[0]
                skill = library.get(name)
                second = executor.execute(intent, k=4)
                print('SECOND:', json.dumps(asdict(second), ensure_ascii=False, default=str), flush=True)
                assert first.learned_skill in second.retrieved_skills and second.critique.success
                assert generator.generate.call_count == 2
                assert critic.check.call_count == 2
                logs = docker('logs', names['gateway'])
                for service_id in service_ids:
                    assert '/services/' + service_id + '/' in logs
                report = dict(case=case, intent=asdict(intent), first=asdict(first), second=asdict(second),
                              skill=asdict(skill), generator_calls=2,
                              gateway_logs=logs, pinned_sources=[{key: entry[key] for key in
                                  ('dataset','revision','ttl_file','ttl_sha256')} for entry in manifest['sources']])
                (tmp_path / 'service_learning_report.json').write_text(
                    json.dumps(report, ensure_ascii=False, default=str, indent=2))
            except subprocess.CalledProcessError as error:
                print('SANDBOX STDERR:', error.stderr, flush=True)
                raise
            finally:
                print('GATEWAY:', docker('logs', names['gateway']), flush=True)


def test_pinned_geosparql_blocks_federation_and_worker_direct_access():
    with network_topology(isolated=True, gateway_code=gateway_code(), worker_image=WORKER_IMAGE,
                          include_origin=False) as names:
        wait_for_gateway(names['gateway'])
        with pinned_geosparql(names):
            # Local request only: SERVICE must be refused before any DNS/network lookup.
            code = '''
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
query = 'SELECT * WHERE { SERVICE <http://gateway:8000/federation-probe> { ?s ?p ?o } }'
try:
    urlopen('http://geosparql:3030/geo/sparql?' + urlencode({'query':query}),timeout=5)
except HTTPError as error:
    message = error.read().decode()
    print(message)
    assert error.code == 422
else:
    raise AssertionError('SPARQL federation was permitted')
'''
            print(docker('exec', names['gateway'], 'python', '-c', code), flush=True)
            assert '/federation-probe' not in docker('logs', names['gateway'])
