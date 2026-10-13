"""Stage 2 of a staged run: one step of an earlier run, executed again on its own.

    .venv/bin/python -m bench.stage_step --trace RUN/NNN/trace.json --step N --out DIR [--library DIR]
    .venv/bin/python -m bench.stage_step --text INTENT --resources ID [ID ...] --out DIR

The step's Intent (its text and resources) is taken from the trace and given to the IntentExecutor as a full run
would: Skill retrieval, code generation, the sandbox, repair, the step Critic. Earlier Observations are not given,
so a step that reads them is not a fit. Every model call is at temperature zero, so a step whose Generator prompt
is the same gives the same code; a step is tried again here until it is sound, without running its Goal.
DIR gets the model calls and result.json.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import time

from bench.infra import benchmark_environment
from bench.run_goals import logged_llm
from geo_voyager.critic import Critic
from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.intent import Intent
from geo_voyager.intent_executor import IntentExecutor
from geo_voyager.services import load_service_graph
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
from geo_voyager.skill_candidate_repairer import SkillCandidateRepairer
from geo_voyager.skill_library import SkillLibrary
from geo_voyager.skill_retriever import SkillRetriever
from geo_voyager.worker import Worker


def step_intent(trace: dict, number: int) -> Intent:
    step = next(event for event in trace['events'] if event.get('kind') == 'step' and event['step'] == number)
    services = {service.id for service in load_service_graph().all()}
    return Intent(step['intent'], dataset_ids=tuple(r for r in step['resources'] if r not in services),
                  service_ids=tuple(r for r in step['resources'] if r in services))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--trace')
    parser.add_argument('--step', type=int)
    parser.add_argument('--text', help='an Intent written for the test, instead of a step of a trace')
    parser.add_argument('--resources', nargs='*', default=[])
    parser.add_argument('--out', required=True)
    parser.add_argument('--library', help="a Skill library to copy; the repository's seed Skills when omitted")
    args = parser.parse_args()
    if args.text:
        services = {service.id for service in load_service_graph().all()}
        intent = Intent(args.text, dataset_ids=tuple(r for r in args.resources if r not in services),
                        service_ids=tuple(r for r in args.resources if r in services))
    else:
        intent = step_intent(json.loads(Path(args.trace).expanduser().read_text()), args.step)
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=False)
    library = out / 'library'
    shutil.copytree(Path(args.library).expanduser() if args.library else Path(__file__).resolve().parents[1] / 'skill_library',
                    library, ignore=shutil.ignore_patterns('embedding.json'))
    llm = logged_llm(out)
    critic = Critic(llm)
    embedding = EmbeddingClient(os.environ['GEO_VOYAGER_EMBEDDING_BASE_URL'], os.environ['GEO_VOYAGER_EMBEDDING_MODEL'])
    started = time.time()
    with benchmark_environment() as names:
        skills = SkillLibrary(library)
        executor = IntentExecutor(SkillRetriever(skills, embedding), Worker(names['internal']),
                                  SkillCandidateGenerator(llm), critic, skills, SkillCandidateRepairer(llm))
        try:
            execution = executor.execute(intent)
        except ValueError as problem:
            result = {'intent': intent.text, 'refused': str(problem), 'elapsed': round(time.time() - started, 1)}
            (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
            print(json.dumps(result, ensure_ascii=False, indent=1))
            return
    result = {'intent': intent.text, 'resources': [*intent.dataset_ids, *intent.service_ids],
              'succeeded': execution.failure is None, 'critic_success': execution.critique.success,
              'critic_reason': execution.critique.reason,
              'failure': (execution.failure.message + ' ' + execution.failure.stderr[-400:]) if execution.failure is not None else None,
              'observations': [observation.text[:2000] for observation in execution.observations],
              'attempts': [{'code': attempt.code, 'failure': attempt.failure.message if attempt.failure is not None else None}
                           for attempt in execution.attempts],
              'elapsed': round(time.time() - started, 1)}
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != 'attempts'}, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
