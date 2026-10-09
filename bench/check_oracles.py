"""Run every Goal's oracle once and print its output.

    .venv/bin/python -m bench.check_oracles [--ids a,b]

Run this before a benchmark: an oracle that errors or returns something odd makes a whole
Goal unmeasurable (or worse, wrongly judged).
"""
import argparse

from bench.goals import GOALS
from bench.infra import benchmark_environment
from bench.run_goals import run_oracle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ids', default='')
    wanted = [item for item in parser.parse_args().ids.split(',') if item]
    failures = 0
    with benchmark_environment() as names:
        for goal in GOALS:
            if wanted and goal.id not in wanted:
                continue
            try:
                output = run_oracle(goal.oracle_code, names['internal'])
                print(f'OK   {goal.id}: {output}', flush=True)
            except Exception as error:
                failures += 1
                detail = getattr(error, 'stderr', None) or str(error)
                if isinstance(detail, bytes):
                    detail = detail.decode(errors='replace')
                print(f'FAIL {goal.id}: {type(error).__name__}: {detail.strip()[-400:]}', flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
