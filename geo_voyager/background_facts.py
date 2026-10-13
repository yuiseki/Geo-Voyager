"""Background facts: what the loop is given to know before it explores (a seed of the World Graph, which holds what
it finds out). Each fact was checked on the data, and says how and when, in background_facts.jsonl, one per line.

The edge cases of a place do not belong in the How-to Graph (GeoAI-skills), which keeps general procedures and the
facts of datasets: there would be no end to them. A fact is shown when the text names one of its terms, so a prompt
carries only the few a Goal needs.
"""
import json
from pathlib import Path

FACTS = [json.loads(line) for line in Path(__file__).with_name('background_facts.jsonl').read_text(encoding='utf-8').splitlines()
         if line.strip()]


def facts_for(text: str) -> list[str]:
    return [fact['fact'] for fact in FACTS if any(term in text for term in fact['terms'])]


def facts_section(text: str) -> str:
    """The facts the text names, as a section of a prompt, or '' when there are none."""
    facts = facts_for(text)
    return ('前提知識（データで確かめた事実）:\n' + ''.join(f'- {fact}\n' for fact in facts)) if facts else ''
