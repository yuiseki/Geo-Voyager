"""Detect a repaired candidate that pastes in values it was shown instead of computing them.

A semantic repair sees the observation that was judged wrong, the observations before it and the
Critic's reason. A model can "fix" the answer by writing the value it saw into the code. Such a
literal is flagged when the repaired code has it, the original code did not, and it is a value
(not a key) of one of the texts the repair was shown.
"""
import ast
import json
import re

MIN_DIGITS = 3
MIN_ASCII_LENGTH = 3
_NUMBER = re.compile(r'\d+(?:\.\d+)?')


def _constants(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
            if isinstance(node.value, (str, int, float)):
                found.add(str(node.value))
    return found


def _json_values(value) -> set[str]:
    if isinstance(value, dict):
        return set().union(*(_json_values(item) for item in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_json_values(item) for item in value)) if value else set()
    if isinstance(value, bool) or value is None:
        return set()
    return {str(value)}


def _significant(text: str) -> bool:
    if _NUMBER.fullmatch(text):
        return len(text.replace('.', '')) >= MIN_DIGITS or '.' in text
    return len(text) >= (MIN_ASCII_LENGTH if text.isascii() else 2)


def observed_values(texts: list[str]) -> set[str]:
    values = set()
    for text in texts:
        try:
            values |= _json_values(json.loads(text))
        except ValueError:
            pass
        values |= {number for number in _NUMBER.findall(text) if len(number.replace('.', '')) >= MIN_DIGITS or '.' in number}
    return {value for value in values if _significant(value)}


def hardcoded_literals(new_code: str, old_code: str, evidence: list[str]) -> set[str]:
    return (_constants(new_code) - _constants(old_code)) & observed_values(evidence)
