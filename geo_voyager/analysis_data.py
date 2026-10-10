"""The data the analysis sandbox reads, fixed on the host and mounted read-only at /data.

Each file is fetched once from a pinned revision of its source and checked by its SHA-256, so every run, and the
reference solutions that confirm the oracle numbers, read the same bytes. The files are not kept in this repository
(some are CC BY-SA); this catalog records where they come from.
"""
from dataclasses import dataclass
import os
from pathlib import Path

DEFAULT_ROOT = '/sata_hdd_24tb/data/geo-voyager/analysis'


@dataclass(frozen=True)
class AnalysisFile:
    path: str          # under the data root, and under /data in the sandbox
    url: str           # a URL that names a fixed revision
    sha256: str
    size: int
    license: str
    note: str


FILES = (
    AnalysisFile(
        'michiyomi/taito.parquet',
        'https://huggingface.co/datasets/finalvent/michiyomi-tokyo-streetscape/resolve/'
        'e4966cdceff6b0a2e3cb37e6a7efcc2b07eeba44/data/scenes/taito.parquet',
        '5a572f7a6dc8042591f32151c17bf387d83aa200ab1b4ae8ce7dea2997d40096', 59_739_579,
        'CC BY-SA 4.0 (© Mapillary contributors, processed; 国土数値情報 A29 and P29; 東京都建設局)',
        'michiyomi release 2026-09-13-r1. Street scenes read by a VLM; one file per municipality.'),
    AnalysisFile(
        'jp-admin/municipalities.parquet',
        'https://huggingface.co/datasets/yuiseki/jp-admin-2026-09/resolve/'
        'e6c87b1d7095c17422147962185071a986e13135/municipalities.parquet',
        'cd3cde88e5b70f26bef9f4d04405422540e33651461eaf1192f475dd8db2e68e', 148_639_909,
        'CC BY 4.0',
        'Municipal boundaries (EPSG:4612) and 2020 census population; the revision Geo-Voyager already pins.'),
)


def data_root() -> Path:
    return Path(os.environ.get('GEO_VOYAGER_ANALYSIS_DATA', DEFAULT_ROOT))
