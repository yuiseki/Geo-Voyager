"""Run benchmark goals against the real LLM, Docker sandbox and registered services.

    .venv/bin/python -m bench.run_goals --out ~/tmp/geo-voyager-bench/run1 [--ids a,b] [--repeat N]

Every Goal starts from an empty Skill Library so each Intent goes through the Generator and
Repairer. One JSON row per Goal is appended to results.jsonl; LLM prompts and responses are
kept under <out>/<goal id>.r<round>/ for later failure analysis.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import time
from unittest.mock import Mock

from bench.goals import GOALS
from geo_voyager.critic import Critic
from geo_voyager.docker_sandbox import DockerSandbox
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.llama_client import LlamaClient
from geo_voyager.planner import Planner
from geo_voyager.repair_stats import intent_record
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.skill_selector import SkillSelector
from geo_voyager.worker import Worker
from bench.infra import WORKER_IMAGE, benchmark_environment

ORACLE_ATTEMPTS = 3


def run_oracle(code: str, network: str) -> dict:
    """Services fail transiently; an oracle that never answers makes the Goal unmeasurable."""
    for attempt in range(ORACLE_ATTEMPTS):
        try:
            return json.loads(DockerSandbox(image=WORKER_IMAGE, network=network).run(code))
        except Exception:
            if attempt == ORACLE_ATTEMPTS - 1:
                raise
            time.sleep(2)


def logged_llm(directory: Path) -> Mock:
    directory.mkdir(parents=True, exist_ok=True)
    llm = Mock(wraps=LlamaClient())
    generate = llm.generate._mock_wraps

    def log(*args, **kwargs):
        number = llm.generate.call_count
        (directory / f'llm_{number:02d}_prompt.txt').write_text(args[0])
        reply = generate(*args, **kwargs)
        (directory / f'llm_{number:02d}_response.txt').write_text(reply)
        return reply
    llm.generate.side_effect = log
    return llm


def run_goal(goal, names, directory: Path, embedding: EmbeddingClient, *, critic_thinking: bool = False) -> dict:
    # One directory per run: a shared Skill Library would let later rounds reuse earlier skills.
    directory.mkdir(parents=True, exist_ok=False)
    library_path = directory / 'skill_library'
    library_path.mkdir(exist_ok=True)
    library = SkillLibrary(library_path)
    llm = logged_llm(directory)
    critic = Critic(llm, thinking=critic_thinking)
    executor = IntentExecutor(SkillRetriever(library, embedding), SkillSelector(llm),
                              Worker(names['internal']), SkillCandidateGenerator(llm),
                              critic, library, SkillCandidateRepairer(llm))
    started = time.time()
    row = {'id': goal.id, 'goal': goal.text, 'started': started, 'critic_thinking': critic_thinking,
           'commit': subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip(),
           'required': list(goal.required), 'target_relation': goal.target_relation}
    try:
        result = GoalExecutor(Planner(llm), executor, critic).execute(goal.text)
    except Exception as error:  # a planning or infrastructure error is data too
        row.update(error=f'{type(error).__name__}: {error}', intents=[], goal_critic_success=False,
                   correct=False, elapsed=time.time() - started)
        return row
    row['elapsed'] = time.time() - started
    row['intents'] = [dict(intent_record(intent.text, execution), services=list(intent.service_ids),
                           datasets=list(intent.dataset_ids), requires_context=intent.requires_context)
                      for intent, execution in zip(result.intents, result.executions)]
    row['planned_intents'] = len(result.intents)
    row['goal_critic_success'] = result.critique.success
    row['goal_critic_reason'] = result.critique.reason
    final = result.executions[-1].observations[0].text if result.executions[-1].observations else ''
    row['final_observation'] = final[:2000]
    (directory / 'goal_report.json').write_text(
        json.dumps(asdict(result), ensure_ascii=False, default=str, indent=2))
    try:
        oracle = run_oracle(goal.oracle_code, names['internal'])
        row['oracle'] = oracle
        row['correct'] = bool(final) and goal.judge(final, oracle)
    except Exception as error:
        row.update(oracle_error=f'{type(error).__name__}: {error}', correct=None)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--ids', default='')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--critic-thinking', action='store_true')
    args = parser.parse_args()
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    wanted = [item for item in args.ids.split(',') if item]
    goals = [goal for goal in GOALS if not wanted or goal.id in wanted]
    unknown = set(wanted) - {goal.id for goal in GOALS}
    if unknown:
        raise SystemExit(f'unknown goal ids: {sorted(unknown)}')
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'],
                                os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    with benchmark_environment() as names:
        for round_number in range(1, args.repeat + 1):
            for goal in goals:
                run_id = f'{goal.id}.r{round_number}'
                row = run_goal(goal, names, out / run_id, embedding, critic_thinking=args.critic_thinking)
                row['id'], row['round'] = goal.id, round_number
                with (out / 'results.jsonl').open('a') as file:
                    file.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
                print(run_id, 'correct=', row.get('correct'), 'critic=', row.get('goal_critic_success'),
                      'intents=', [(r['outcome_at'], r['failure_types']) for r in row['intents']],
                      'error=', row.get('error'), flush=True)


if __name__ == '__main__':
    main()
