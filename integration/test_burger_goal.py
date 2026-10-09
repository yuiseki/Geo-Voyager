"""Explicit real-LLM/service test. Learned skills stay in a temporary library."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from geo_voyager.critic import Critic
from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.llama_client import LlamaClient
from geo_voyager.planner import Planner
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from geo_voyager.worker import Worker
from integration.network_topology import network_topology
from integration.service_gateway_setup import gateway_code, wait_for_gateway
from integration.test_service_learning import pinned_geosparql
from integration.test_tokyo23_gateway import docker

def target_rows(text):
    """Rows with name and relation_id, from a JSON list or from a list inside a JSON object."""
    try:
        value = json.loads(text)
    except ValueError:
        return []
    candidates = [value] if isinstance(value, list) else list(value.values()) if isinstance(value, dict) else []
    for items in candidates:
        if (isinstance(items, list) and items and all(isinstance(row, dict) and 'name' in row and 'relation_id' in row for row in items)):
            return items
    return []


GOAL = '東京23区で cuisine=burger の OSM 地物数が最も多い区を求める。全23区の件数と最多の区名・件数を示す。'


def test_burger_goal_repairs_learns_and_reuses_without_manual_code_edits(tmp_path):
    base = os.environ.get('GEO_VOYAGER_EMBEDDING_BASE_URL')
    model = os.environ.get('GEO_VOYAGER_EMBEDDING_MODEL')
    if not base or not model:
        pytest.skip('Configure local embedding endpoint explicitly')
    library_path = tmp_path / 'skill_library'; library_path.mkdir()
    library = SkillLibrary(library_path)
    llm = Mock(wraps=LlamaClient())
    generate = llm.generate._mock_wraps
    def log_llm(*args, **kwargs):
        number = llm.generate.call_count
        (tmp_path / f'llm_{number}_prompt.txt').write_text(args[0])
        reply = generate(*args, **kwargs)
        (tmp_path / f'llm_{number}_response.txt').write_text(reply)
        return reply
    llm.generate.side_effect = log_llm
    generator = Mock(wraps=SkillCandidateGenerator(llm))
    original_generate = generator.generate._mock_wraps
    injected = []
    def generate_candidate(intent):
        candidate = original_generate(intent)
        (tmp_path / f'generated_{generator.generate.call_count}.py').write_text(candidate.code)
        # Fault injection is deliberate; repairs still use the real LLM exclusively.
        if generator.generate.call_count == 1:
            candidate = replace(candidate, code='if :\n' + candidate.code)
            injected.append(candidate)
        return candidate
    generator.generate.side_effect = generate_candidate
    planner = Planner(llm)
    repairer = Mock(wraps=SkillCandidateRepairer(llm))
    critic = Critic(llm)
    with network_topology(isolated=True, gateway_code=gateway_code(),
                          worker_image='geo-voyager-worker:duckdb-1.5.6', include_origin=False) as names:
        wait_for_gateway(names['gateway'])
        with pinned_geosparql(names):
            retriever = SkillRetriever(library, EmbeddingClient(base, model))
            executor = IntentExecutor(retriever, SkillSelector(llm), Worker(names['internal']),
                                      generator, critic, library, repairer)
            logged = Mock(wraps=executor)
            execute = logged.execute._mock_wraps
            step_results = []
            def execute_logged(intent):
                number = logged.execute.call_count
                print(f'STEP {number}: {intent.text}', flush=True)
                generations_before = generator.generate.call_count
                result = execute(intent)
                generation_delta = generator.generate.call_count - generations_before
                if result.selected_skill_critique and result.selected_skill_critique.success:
                    assert generation_delta == 0
                step_results.append(result)
                report = dict(intent=asdict(intent), execution=asdict(result), generator_calls=generation_delta)
                (tmp_path / f'step_{number}.json').write_text(json.dumps(report, ensure_ascii=False, default=str, indent=2))
                print(json.dumps(dict(selected=result.selected_skill_id, learned=result.learned_skill_id,
                                      critique=asdict(result.critique), attempts=len(result.attempts),
                                      observations=[obs.text for obs in result.observations]),ensure_ascii=False,default=str), flush=True)
                return result
            logged.execute.side_effect = execute_logged
            try:
                result = GoalExecutor(planner, logged, critic).execute(GOAL)
                (tmp_path / 'goal_report.json').write_text(json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2))
                assert result.critique.success
                assert any(attempt.failure is not None for step in result.executions for attempt in step.attempts)
                assert repairer.repair.call_count >= 1
                # A target is named by its name and found by identity, never by a list position.
                assert not any('番目' in intent.text for intent in result.intents)
                listings = [rows for step in result.executions for observation in step.observations
                            for rows in [target_rows(observation.text)] if rows]
                assert listings, 'some step must output the targets with name and relation_id'
                wards = listings[0]
                assert len(wards) == 23 and len({str(row['relation_id']) for row in wards}) == 23
                assert all(row['name'].endswith('区') for row in wards)
                # Independent live verification only. This code is not a learned Skill,
                # never enters Planner/Generator/Repairer, and provides no answer to them.
                areas = [int(row['relation_id']) + 3600000000 for row in wards]
                expected = {}
                for start in range(0, len(areas), 6):
                    chunk = areas[start:start + 6]
                    oracle = ('from geo_voyager.control_primitives import call_service\nimport json\n'
                              'counts=[]\nfor area_id in ' + repr(chunk) + ':\n'
                              '    query=\'[out:json][timeout:12];nwr["cuisine"="burger"](area:\'+str(area_id)+\');out count;\'\n'
                              '    response=json.loads(call_service("overpass",path="/api/interpreter",body=query,content_type="text/plain"))\n'
                              '    assert not response.get("remark") and len(response["elements"])==1\n'
                              '    counts.append(int(response["elements"][0]["tags"]["total"]))\n'
                              'print(json.dumps({"counts":counts,"timestamp":response["osm3s"]["timestamp_osm_base"]}))')
                    raw = DockerSandbox(image='geo-voyager-worker:duckdb-1.5.6', network=names['internal']).run(oracle)
                    response = json.loads(raw)
                    for ward, count in zip(wards[start:start + 6], response['counts']):
                        expected[ward['relation_id']] = count
                measured = {}
                for rows in listings:
                    for row in rows:
                        if 'count' in row:
                            measured[str(row['relation_id'])] = row['count']
                expected = {str(key): count for key, count in expected.items()}
                assert measured == expected
                maximum = max(expected.values())
                winners = {ward['name'] for ward in wards if expected[str(ward['relation_id'])] == maximum}
                final_text = result.executions[-1].observations[0].text
                assert any(name in final_text for name in winners) and str(maximum) in final_text
                (tmp_path / 'verified_counts.json').write_text(json.dumps(dict(measured=measured, maximum=maximum, data_time=response['timestamp']), ensure_ascii=False, indent=2))
                print('FINAL:', result.critique, flush=True)
            finally:
                (tmp_path / 'gateway.log').write_text(docker('logs', names['gateway']))
