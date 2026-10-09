"""Summarise a benchmark run: python -m bench.report <results.jsonl> [...]"""
import json
from pathlib import Path
import sys

from geo_voyager.repair_stats import summarize, summarize_goals


def load(paths: list[str]) -> list[dict]:
    return [json.loads(line) for path in paths
            for line in Path(path).expanduser().read_text().splitlines() if line.strip()]


def main() -> None:
    rows = load(sys.argv[1:])
    intents = [intent for row in rows for intent in row['intents']]
    print(json.dumps({'goals': summarize_goals(rows), 'intents': summarize(intents)},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
