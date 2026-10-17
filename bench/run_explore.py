"""Free exploration: the curriculum proposes a Goal, the step-by-step route answers it, the finding is kept. Repeat.

    .venv/bin/python -m bench.run_explore --out DIR --library DIR --goals N
    .venv/bin/python -m bench.run_explore --out DIR --library DIR --replay FILE
    .venv/bin/python -m bench.run_explore --out DIR --library DIR --resume --goals 0   # only take up stopped Goals

--replay takes the Goals from FILE (one per line) instead of the curriculum, to compare a change on the Goals an
earlier exploration tried.

There is no list of Goals and no oracle. The Skill library, the World Graph (DIR/world.jsonl, the answered Goals with
their provenance) and the record of every Goal tried (DIR/exploration.jsonl) carry over from Goal to Goal, and
across runs given the same --out and --library, so a run can be continued. Each Goal's events are written as they
happen to DIR/NNN/events.jsonl (geo_voyager.event_log); a Goal that broke on the way has no end there.
"""
import argparse
import datetime
import json
import os
import random
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
from geo_voyager.event_log import EventLog, LoggedGoal
from geo_voyager.exploration_graph import ExplorationGraph
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.goal_executor import GoalExecutor
from geo_voyager.ingredients import draw
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.planner import Planner
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.worker import Worker
from geo_voyager.world_graph import WorldGraph

CURRICULUM_TRIES = 3


def propose(curriculum: Curriculum, findings: list[dict], attempts: list[dict], ingredients=None):
    note = None
    for _ in range(CURRICULUM_TRIES):
        try:
            return curriculum.propose(findings, attempts, note=note, ingredients=ingredients)
        except CurriculumRejected as rejected:
            note = f'前回の応答は使えなかった: {rejected.reason}'
    return None


def unfinished(out: Path) -> list[tuple[int, LoggedGoal]]:
    """The Goals of the directory whose log has no end (the run stopped on them), in their order."""
    found = []
    for directory in sorted(path for path in out.iterdir() if path.is_dir() and path.name.isdigit()):
        if (directory / 'events.jsonl').exists():
            logged = EventLog(directory / 'events.jsonl').read()
            if not logged.ended:
                found.append((int(directory.name), logged))
    return found


def still_to_replay(goals: list, out: Path) -> list:
    """The Goals of a replay after those the directory has begun: one Goal directory each, in order."""
    begun = sum(1 for path in out.iterdir() if path.is_dir() and path.name.isdigit()) if out.exists() else 0
    return goals[begun:]


def explore_one(number: int, out: Path, names, library: SkillLibrary, embedding: EmbeddingClient,
                world: WorldGraph, exploration: ExplorationGraph, given: ProposedGoal | None = None, memory: str | None = None,
                resumed: LoggedGoal | None = None) -> dict | None:
    """Explore one Goal: the given one, the curriculum's, or one taken up from its log (resumed), which goes on from
    the events written before it stopped, with the memory it was given then."""
    directory = out / f'{number:03d}'
    directory.mkdir(parents=True, exist_ok=resumed is not None)
    llm = logged_llm(directory)
    if resumed is not None:
        given, memory = ProposedGoal(resumed.goal, resumed.reason, resumed.prediction), resumed.memory
    # Odd Goals explore, from ingredients drawn by their number; even Goals dig where predictions failed (ADR 0014).
    drawn = draw(random.Random(number)) if given is None and number % 2 == 1 else None
    proposed = given or propose(Curriculum(llm, embedding=embedding), world.findings(), exploration.attempts(), drawn)
    if proposed is None:
        return None
    critic = Critic(llm)
    executor = IntentExecutor(SkillRetriever(library, embedding), Worker(names['internal']),
                              SkillCandidateGenerator(llm), critic, library, SkillCandidateRepairer(llm))
    # Each event is written as it happens. A Goal that breaks gets no end, so it can be taken up again from its log.
    log = EventLog(directory / 'events.jsonl')
    if resumed is None:
        log.start(proposed.goal, memory, reason=proposed.reason, prediction=proposed.prediction,
                  ingredients={'drawn': list(drawn.names()), 'used': list(proposed.ingredients)} if drawn else None)
    started = time.time()
    try:
        result = GoalExecutor(Planner(llm), executor, critic).execute_adaptive(
            proposed.goal, memory=memory, on_event=log.append, events=resumed.events if resumed is not None else ())
    except Exception as problem:
        # One Goal that breaks (a model call that times out, say) is recorded as tried and the exploration goes on.
        result = None
        error = f'{type(problem).__name__}: {problem}'
    at = datetime.datetime.now().isoformat(timespec='seconds')
    elapsed = round(time.time() - started, 1)
    if result is None:
        return exploration.record(number, None, goal=proposed.goal, success=False, explored_at=at, elapsed=elapsed,
                                  error=error, curriculum_reason=proposed.reason, memory=memory is not None,
                                  prediction=proposed.prediction)
    log.end(result.stop_reason, success=WorldGraph.answered(result))
    # The records are made from the log, the steps before a stop included, as if the Goal had never stopped.
    logged = log.read()
    finding = world.record(logged, explored_at=at, prediction=logged.prediction)
    attempt = exploration.record(number, logged, success=finding is not None, explored_at=at, elapsed=elapsed,
                                 curriculum_reason=proposed.reason, memory=memory is not None,
                                 prediction=proposed.prediction, surprise=finding['surprise'] if finding else None)
    (directory / 'trace.json').write_text(json.dumps(
        {'goal': logged.goal, 'steps': trace_steps(logged), 'events': trace_events(logged)}, ensure_ascii=False, indent=1))
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
    parser.add_argument('--remember', help="an earlier run's --out: a Goal it did not answer is given the failures of that try "
                                           'checked without a model (ADR 0011)')
    parser.add_argument('--resume', action='store_true',
                        help='first take up the Goals of --out that stopped on the way, each from the step after its last event')
    args = parser.parse_args()
    memories = ExplorationGraph(Path(args.remember).expanduser() / 'exploration.jsonl').memories() if args.remember else {}
    out = Path(args.out).expanduser()
    # Given the same --out again, a replay goes on after the Goals it has begun (those stopped on the way: --resume).
    replayed = (still_to_replay([ProposedGoal(line.strip(), 'replay') for line in Path(args.replay).read_text().splitlines()
                                 if line.strip()], out) if args.replay else None)
    out.mkdir(parents=True, exist_ok=True)
    shared = Path(args.library).expanduser()
    if not shared.exists():
        shutil.copytree(Path(__file__).resolve().parents[1] / 'skill_library', shared,
                        ignore=shutil.ignore_patterns('embedding.json'))
    world, exploration = WorldGraph(out / 'world.jsonl'), ExplorationGraph(out / 'exploration.jsonl')
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'], os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    first = sum(1 for path in out.iterdir() if path.is_dir() and path.name.isdigit()) + 1
    exit_on_sigterm()
    taken_up = unfinished(out) if args.resume else []
    new = range(first, first + (len(replayed) if replayed is not None else args.goals))
    with benchmark_environment() as names:
        for index, (number, resumed) in enumerate([*taken_up, *((number, None) for number in new)]):
            if stop_requested(out):
                print(number, f'| stopped by {out / STOP_FILE}', flush=True)
                break
            problem = environment_problem(names)
            if problem:
                print(number, f'| stopped: the environment is gone: {problem}', flush=True)
                sys.exit(1)
            given = replayed[index - len(taken_up)] if replayed is not None and resumed is None else None
            attempt = explore_one(number, out, names, SkillLibrary(shared), embedding, world, exploration,
                                  given, memories.get(given.goal) if given else None, resumed=resumed)
            if attempt is None:
                print(number, '| the curriculum gave no usable Goal', flush=True)
                continue
            print(number, '|', attempt['goal'], '|', 'answered' if attempt['success'] else attempt['stop_reason'],
                  '|', attempt['steps'], 'steps |', attempt['elapsed'], 's', '(taken up)' if resumed else '', flush=True)


if __name__ == '__main__':
    main()
