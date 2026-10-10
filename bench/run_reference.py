"""Run a reference solution in the analysis sandbox and compare it with the study-geoai oracle.

    PYTHONPATH=. .venv/bin/python -m bench.run_reference G1 bench/reference/g1_undergrounding.py

The fixed data (geo_voyager.analysis_data) is mounted read-only; an empty output directory is made under
~/tmp/geo-voyager-analysis-out/. Prints the answer, one line per oracle check, and the time taken.
"""
import json
from pathlib import Path
import sys
import time

from bench.study_oracles import compare
from geo_voyager.analysis_data import data_root
from geo_voyager.docker_sandbox import ANALYSIS_PROFILE, DockerSandbox
from dataclasses import replace

ANALYSIS_IMAGE = 'geo-voyager-analysis:2026-10-10'


def main() -> int:
    goal, script = sys.argv[1], Path(sys.argv[2])
    out = Path.home() / 'tmp' / 'geo-voyager-analysis-out' / f'{goal}-{time.strftime("%Y%m%d-%H%M%S")}'
    out.mkdir(parents=True)
    out.chmod(0o777)        # the sandbox writes as UID 65534
    profile = replace(ANALYSIS_PROFILE, data_dir=str(data_root()), out_dir=str(out))
    started = time.time()
    stdout = DockerSandbox(image=ANALYSIS_IMAGE, profile=profile).run(script.read_text())
    elapsed = time.time() - started
    answer = json.loads(stdout.strip().splitlines()[-1])
    print(json.dumps(answer, ensure_ascii=False))
    rows = compare(goal, answer)
    for row in rows:
        print(('ok  ' if row['ok'] else 'NG  ') + f"{row['key']}: expected {row['expected']} ± {row['tolerance']}, got {row['answer']}")
    print(f'{sum(r["ok"] for r in rows)} / {len(rows)} within tolerance, {elapsed:.1f} s, output in {out}')
    return 0 if all(r['ok'] for r in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
