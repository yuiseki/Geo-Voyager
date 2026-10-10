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
