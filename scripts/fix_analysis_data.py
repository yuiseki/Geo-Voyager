"""Fetch the analysis data at its pinned revisions and check it: python scripts/fix_analysis_data.py [--check]

A file already in place is only checked. A file whose SHA-256 differs is an error, never overwritten.
"""
import hashlib
import sys
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo_voyager.analysis_data import FILES, data_root  # noqa: E402

USER_AGENT = 'Geo-Voyager/0.1 (+https://github.com/yuiseki/Geo-Voyager)'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, target: Path) -> None:
    partial = target.with_name(target.name + '.partial')
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=60) as response, partial.open('wb') as out:
        while block := response.read(1 << 20):
            out.write(block)
    partial.rename(target)


def main() -> int:
    check_only = '--check' in sys.argv
    root, failed = data_root(), 0
    for item in FILES:
        target = root / item.path
        if not target.exists():
            if check_only:
                print('missing', item.path); failed += 1; continue
            print('fetching', item.path, flush=True)
            fetch(item.url, target)
        digest = sha256(target)
        if digest != item.sha256 or target.stat().st_size != item.size:
            print('MISMATCH', item.path, digest, target.stat().st_size); failed += 1
        else:
            print('ok', item.path)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
