"""The indicator codes of the World Bank's WDI, to refuse one the data does not have before anything runs.

The model writes indicator codes from memory, and some are wrong (EN.LND.TOTL.K2 for the land area, which the WDI
calls AG.LND.TOTL.K2). A filter on a wrong code matches no row, and the code reports the value as missing. The codes
are those of the series table at the pinned revision (scripts/sync_wdi_indicators.py).
"""
import difflib
from pathlib import Path
import re

PATH = Path(__file__).with_name('wdi_indicators.tsv')
DATASET = 'yuiseki/worldbank-wdi'
INDICATORS = dict(line.split('\t', 1) for line in PATH.read_text(encoding='utf-8').splitlines()[1:] if line)
# A code is two or three capitals and at least two more parts after dots (SP.POP.TOTL, NY.GDP.PCAP.PP.KD).
_CODE = re.compile(r'(?<![A-Za-z0-9_.])[A-Z]{2,3}(?:\.[A-Z0-9]{2,}){2,}(?![A-Za-z0-9_])')
CLOSE = 4


def unknown_indicators(text: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Each code in the text that the WDI does not have, with the codes closest to it and their names."""
    found = []
    for code in dict.fromkeys(_CODE.findall(text)):
        if code not in INDICATORS:
            close = difflib.get_close_matches(code, INDICATORS, n=CLOSE, cutoff=0.6)
            found.append((code, [(near, INDICATORS[near]) for near in close]))
    return found


def unknown_indicator_text(found: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """The refusal: each code the WDI lacks, the close ones by name, and where the codes are."""
    parts = [f'{code}（近い指標: ' + '、'.join(f'{near} {name}' for near, name in close) + '）' if close else code
             for code, close in found]
    return (f'WDI に無い指標のコード: {"; ".join(parts)}。指標のコードを記憶で書かない。'
            'series の表（Series Code と Indicator Name）にあるコードを使う')
