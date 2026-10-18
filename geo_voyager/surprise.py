"""How far the answer of a Goal was from what the curriculum predicted before it was explored (ADR 0014).

The curriculum predicts the main value of each Goal it proposes, a number or a name. The surprise of the answer is the
reward that gives it curiosity: where its predictions fail, the world is not as it thought, and there is more to learn.
It is measured without a model, so that no model's judgement reaches the curriculum (ADR 0011).

- A number: how many tens the answer is off by, |log10(answer / prediction)|, up to 1 (ten times or more). The answer
  may hold several numbers and which one the prediction meant is not known, so the nearest is taken: the surprise is
  never more than it was.
- A name: 0 when the answer has it, or has a name of three letters or more that ends it (横浜市営地下鉄ブルーライン
  written ブルーライン), 1 when it does not.
"""
import json
import math
import re

# A number as people write it: 3,777,491 / 23.86 / -3, and 万 or 億 after it (約 370 万人, 1.5億).
_NUMBER = re.compile(r'-?\d[\d,]*(?:\.\d+)?\s*[万億]?')
_UNITS = {'万': 10 ** 4, '億': 10 ** 8}
_PLAIN_NUMBER = re.compile(r'-?\d+(?:\.\d+)?')
_QUOTES = '「」『』"\'“”。、 　'


def surprise(prediction: str, answer: str) -> float | None:
    """The surprise of the answer, from 0 (the prediction came true) to 1; None when there is nothing to compare."""
    prediction = prediction.strip()
    if not prediction:
        return None
    found = _NUMBER.search(prediction)
    if found is None:
        name = prediction.removeprefix('約').strip(_QUOTES)
        return (0.0 if name in answer or any(name.endswith(text) for text in _names(answer)) else 1.0) if name else None
    predicted = _value(found.group())
    numbers = _numbers(answer)
    if not numbers:
        return None
    return min(_off(predicted, number) for number in numbers)


def _names(answer: str) -> list[str]:
    """The texts of the answer's JSON of three letters or more, which may name what was predicted."""
    try:
        data = json.loads(answer)
    except ValueError:
        return []
    texts = []

    def walk(value) -> None:
        if isinstance(value, str) and len(value.strip()) >= 3:
            texts.append(value.strip())
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return texts


def _value(text: str) -> float:
    text = text.replace(',', '').replace(' ', '')
    unit = _UNITS.get(text[-1], 1)
    return float(text.rstrip('万億')) * unit


def _off(predicted: float, actual: float) -> float:
    if predicted == actual:
        return 0.0
    if predicted == 0 or actual == 0 or (predicted < 0) != (actual < 0):
        return 1.0
    return min(1.0, abs(math.log10(actual / predicted)))


def _numbers(answer: str) -> list[float]:
    """The numbers of the answer: those of its JSON (written as numbers or as text), or those of its text."""
    try:
        data = json.loads(answer)
    except ValueError:
        return [_value(match.group()) for match in _NUMBER.finditer(answer)]
    numbers = []

    def walk(value) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            numbers.append(float(value))
        elif isinstance(value, str) and _PLAIN_NUMBER.fullmatch(value.strip()):
            numbers.append(float(value))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return numbers
