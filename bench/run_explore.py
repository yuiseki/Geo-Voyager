"""Free exploration: the curriculum proposes a Goal, the step-by-step route answers it, the finding is kept. Repeat.

    .venv/bin/python -m bench.run_explore --out DIR --library DIR --goals N
    .venv/bin/python -m bench.run_explore --out DIR --library DIR --replay FILE

--replay takes the Goals from FILE (one per line) instead of the curriculum, to compare a change on the Goals an
earlier exploration tried.

There is no list of Goals and no oracle. The Skill library, the World Graph (DIR/world.jsonl, the answered Goals with
their provenance) and the record of every Goal tried (DIR/exploration.jsonl) carry over from Goal to Goal, and
across runs given the same --out and --library, so a run can be continued.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

from bench.adaptive_trace import trace_events, trace_steps
from bench.infra import benchmark_environment, environment_problem
from bench.run_goals import logged_llm
from geo_voyager.critic import Critic
from geo_voyager.curriculum import Curriculum, CurriculumRejected, ProposedGoal
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.planner import Planner
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.worker import Worker
from geo_voyager.world_graph import WorldGraph

CURRICULUM_TRIES = 3


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def propose(curriculum: Curriculum, findings: list[dict], attempts: list[dict]):
    note = None
    for _ in range(CURRICULUM_TRIES):
        try:
            return curriculum.propose(findings, attempts, note=note)
        except CurriculumRejected as rejected:
            note = f'前回の応答は使えなかった: {rejected.reason}'
    return None


def explore_one(number: int, out: Path, names, library: SkillLibrary, embedding: EmbeddingClient,
                world: WorldGraph, exploration: Path, given: ProposedGoal | None = None) -> dict | None:
    directory = out / f'{number:03d}'
    directory.mkdir(parents=True, exist_ok=False)
    llm = logged_llm(directory)
    proposed = given or propose(Curriculum(llm), world.findings(), read_jsonl(exploration))
    if proposed is None:
        return None
    critic = Critic(llm)
    executor = IntentExecutor(SkillRetriever(library, embedding), Worker(names['internal']),
                              SkillCandidateGenerator(llm), critic, library, SkillCandidateRepairer(llm))
    started = time.time()
    try:
        result = GoalExecutor(Planner(llm), executor, critic).execute_adaptive(proposed.goal)
    except Exception as problem:
        # One Goal that breaks (a model call that times out, say) is recorded as tried and the exploration goes on.
        result = None
        error = f'{type(problem).__name__}: {problem}'
    at = datetime.datetime.now().isoformat(timespec='seconds')
    finding = world.record(result, explored_at=at) if result is not None else None
    attempt = {'number': number, 'goal': proposed.goal, 'curriculum_reason': proposed.reason, 'success': finding is not None,
               'stop_reason': result.stop_reason if result is not None else 'error',
               'reason': result.critique.reason if result is not None else error,
               'steps': len(result.history) if result is not None else None,
               'elapsed': round(time.time() - started, 1), 'explored_at': at}
    with exploration.open('a') as file:
        file.write(json.dumps(attempt, ensure_ascii=False) + '\n')
    if result is None:
        return attempt
    (directory / 'trace.json').write_text(json.dumps(
        {'goal': proposed.goal, 'steps': trace_steps(result), 'events': trace_events(result)}, ensure_ascii=False, indent=1))
    return attempt


# A file of this name in the output directory stops the run before the next Goal, so a run can end between Goals.
STOP_FILE = 'STOP'


def stop_requested(out: Path) -> bool:
    return (out / STOP_FILE).exists()


def exit_on_sigterm() -> None:
    """Turn SIGTERM into SystemExit. Killed by the default handler, the run left its GeoSPARQL and gateway
    containers behind; exiting through Python lets benchmark_environment remove them."""
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(128 + signum))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--library', required=True, help="made from the repository's seed Skills when it does not exist yet")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument('--goals', type=int, help='how many Goals to explore in this run')
    which.add_argument('--replay', help='a file of Goals, one per line, explored in order instead of asking the curriculum')
    args = parser.parse_args()
    replayed = ([ProposedGoal(line.strip(), 'replay') for line in Path(args.replay).read_text().splitlines() if line.strip()]
                if args.replay else None)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    shared = Path(args.library).expanduser()
    if not shared.exists():
        shutil.copytree(Path(__file__).resolve().parents[1] / 'skill_library', shared,
                        ignore=shutil.ignore_patterns('embedding.json'))
    world, exploration = WorldGraph(out / 'world.jsonl'), out / 'exploration.jsonl'
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'], os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    first = sum(1 for path in out.iterdir() if path.is_dir() and path.name.isdigit()) + 1
    exit_on_sigterm()
    with benchmark_environment() as names:
        for index, number in enumerate(range(first, first + (len(replayed) if replayed else args.goals))):
            if stop_requested(out):
                print(number, f'| stopped by {out / STOP_FILE}', flush=True)
                break
            problem = environment_problem(names)
            if problem:
                print(number, f'| stopped: the environment is gone: {problem}', flush=True)
                sys.exit(1)
            attempt = explore_one(number, out, names, SkillLibrary(shared), embedding, world, exploration,
                                  replayed[index] if replayed else None)
            if attempt is None:
                print(number, '| the curriculum gave no usable Goal', flush=True)
                continue
            print(number, '|', attempt['goal'], '|', 'answered' if attempt['success'] else attempt['stop_reason'],
                  '|', attempt['steps'], 'steps |', attempt['elapsed'], 's', flush=True)


if __name__ == '__main__':
    main()
