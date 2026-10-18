"""Checks of an Intent against the dataset references, without the model.

Stage 1 asked jp-admin for an OSM relation_id now and then whatever the dataset lines said, and once wrote a range of
municipal codes that does not exist. A sentence in a prompt moved with every change of wording; these do not.
"""
import io
import json
from pathlib import Path
import re
import tokenize

from ..intent import Intent

_DATA = json.loads((Path(__file__).parents[1] / 'dataset_references.json').read_text(encoding='utf-8'))

# How an Intent names a key a reference lists under no_key.
_WORDS = {
    'osm_id': ('osm_id', 'osm id', 'osm の id', 'relation_id', 'relation id', 'osm relation', 'osmrelation'),
    'code5': ('code5', '市区町村コード'),
}


def _columns(dataset_id: str) -> set[str]:
    reference = _DATA['datasets'].get(dataset_id, {})
    return {name for table in reference.get('tables', []) for name, _ in table.get('schema', {}).get('columns', [])}


def lacked_keys(intent: Intent) -> list[str]:
    """The keys the Intent asks of its datasets that they say they do not have, with the references' notes. A key
    may come from a declared service or an input result, or from another declared dataset that has the column."""
    if intent.service_ids or intent.inputs:
        return []
    text = intent.text.lower()
    present = set().union(*(_columns(dataset_id) for dataset_id in intent.dataset_ids)) if intent.dataset_ids else set()
    found = {}
    for dataset_id in intent.dataset_ids:
        for table in _DATA['datasets'].get(dataset_id, {}).get('tables', []):
            for key in table.get('no_key', []):
                name = key['name']
                if name not in present and any(word in text for word in _WORDS.get(name, (name,))):
                    found.setdefault(name, f'{dataset_id} は {name} を持たない（{key["note"]}）')
    return list(found.values())


def unsourced_codes(intent: Intent, goal: str, sources: str) -> list[str]:
    """Numbers of five digits or more in the Intent that neither the Goal nor the history gave."""
    return [code for code in dict.fromkeys(re.findall(r'\d{5,}', intent.text)) if code not in goal and code not in sources]


def _without_comments(code: str) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return re.sub(r'#[^\n]*', '', code)
    lines = code.splitlines(keepends=True)
    for token in reversed([token for token in tokens if token.type == tokenize.COMMENT]):
        (row, start), (_, end) = token.start, token.end
        lines[row - 1] = lines[row - 1][:start] + lines[row - 1][end:]
    return ''.join(lines)


# The Earth's radius (mean and equatorial) and the metres in a degree of latitude, which code may know by heart.
_CONSTANTS = frozenset({'6371000', '6378137', '111320', '111319', '111195', '111111'})


def unsourced_numbers(code: str, sources: str) -> list[str]:
    """Numbers of five digits or more in the code, outside its comments, that the sources (what the code was given)
    do not have. A round number (a unit, Overpass's area offset 3600000000), an EPSG code and a constant of the Earth
    are not codes."""
    found = re.findall(r'(?<![\d.])(?<!EPSG:)\d{5,}(?![\d.])', _without_comments(code))
    return [number for number in dict.fromkeys(found)
            if number not in sources and len(number.rstrip('0')) > 2 and number not in _CONSTANTS]
