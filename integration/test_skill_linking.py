"""A program that calls a saved Skill runs in the real Worker: the Skill is linked in front of it, and a failure
inside the program is numbered by the program as it was written. Needs Docker, the worker image and the Internet
(the Gateway resolves the dataset's Parquet URL)."""
import json
from pathlib import Path

from bench.infra import benchmark_environment
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.worker import Worker

SEEDS = SkillLibrary(Path(__file__).resolve().parents[1] / 'skill_library')
ADMIN = Intent('東京都23区で人口が最も多い区を求める', ('yuiseki/jp-admin-2026-09',))


def test_a_program_calling_a_seed_skill_runs_and_a_failure_points_at_the_program_line():
    with benchmark_environment() as names:
        worker = Worker(names['internal'])
        program = 'import json\nprint(json.dumps(most_populous_area(dataset_id, area="東京都23区"), ensure_ascii=False))'
        result = worker.execute_candidate(ADMIN, SkillCandidate(program, '人口最大の区'), SEEDS)
        assert isinstance(result, list) and len(result) == 1
        answer = json.loads(result[0].text)
        assert answer['name'] == '世田谷区' and answer['population'] == 943_664
        broken = 'x = most_populous_area(dataset_id, area="東京都23区")\nprint(x["no_such_key"])'
        failure = worker.execute_candidate(ADMIN, SkillCandidate(broken, '壊れた'), SEEDS)
        assert 'KeyError' in failure.stderr and 'File "<candidate>", line 2' in failure.stderr


def run_seed(worker, intent, call):
    program = f'import json\nprint(json.dumps({call}, ensure_ascii=False))'
    result = worker.execute_candidate(intent, SkillCandidate(program, call), SEEDS)
    assert isinstance(result, list), getattr(result, 'stderr', result)
    return json.loads(result[0].text)


def test_the_service_seeds_answer_as_the_oracles_do():
    """The service Seeds against the real services, with the oracle values of bench/goals.py."""
    from geo_voyager.target_ref import TargetRef
    with benchmark_environment() as names:
        worker = Worker(names['internal'])
        lookup = Intent('区の relation ID', service_ids=('nominatim',), target=TargetRef('港区'))
        assert run_seed(worker, lookup, 'get_relation_id(intent_target)')['relation_id'] == '1761717'
        count = Intent('区のカフェの数', service_ids=('overpass', 'nominatim'), target=TargetRef('渋谷区'))
        assert run_seed(worker, count, 'count_tag_in_area(intent_target, "amenity", "cafe")')['count'] == 459
        usage = Intent('タグの使用数', service_ids=('taginfo',))
        assert run_seed(worker, usage, 'tag_usage_count("cuisine", "ramen")')['count'] == 8213
        route = Intent('経路', service_ids=('valhalla',))
        auto = run_seed(worker, route, 'route_summary(35.6580, 139.7016, 35.6896, 139.7006)')
        walk = run_seed(worker, route, 'route_summary(35.6580, 139.7016, 35.6896, 139.7006, costing="pedestrian")')
        assert abs(auto['length_km'] - 4.547) < 0.01 and abs(walk['time_min'] - 48.406) < 0.5
