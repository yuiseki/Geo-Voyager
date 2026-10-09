"""Detect a repair that hides a missing value behind a default instead of fixing the key.

A runtime repair answers a traceback. For `KeyError: 'count_all'` the right fix is the key the API really has
('count'). The easy wrong fix is `item.get("count_all", 0)`: the run then succeeds and prints 0 where the API said
nothing, and the failure is gone while the answer is wrong. The same goes for a new `except KeyError: pass`.

The rule is about a repair of a failure that is a missing key or index, and about the key the traceback names. A `.get()`
that was already in the original code is the author's choice and is left alone, and so is a `.get()` of another key.
A one-argument `.get(key)` is allowed when the value is then checked out loud (`if x is None: raise`, `assert x`), which
is how an optional field is read honestly. A default (`.get(key, 0)`) is never allowed for the key that was missing.
"""
import ast
from collections import Counter
import re

SWALLOWED = {'KeyError', 'IndexError', 'Exception', 'BaseException'}


def _parse(code: str):
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


def _get_calls(tree) -> Counter:
    calls = Counter()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get'
                and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            calls[(node.args[0].value, len(node.args), ast.unparse(node))] += 1
    return calls


def _checked_out_loud(tree, call_text: str) -> bool:
    """`x = <call>` and later `assert x ...` or `if ... x ...: raise`: the missing value is not silent."""
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and ast.unparse(node.value) == call_text):
            name = node.targets[0].id
            for other in ast.walk(tree):
                if isinstance(other, ast.Assert) and name in ast.unparse(other.test):
                    return True
                if isinstance(other, ast.If) and name in ast.unparse(other.test) \
                        and any(isinstance(inner, ast.Raise) for inner in ast.walk(other)):
                    return True
    return False


def _caught(handler: ast.ExceptHandler) -> set[str]:
    if handler.type is None:
        return {'Exception'}
    members = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return {ast.unparse(member) for member in members}


def _swallowing_handlers(tree) -> Counter:
    found = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _caught(node) & SWALLOWED \
                and not any(isinstance(inner, ast.Raise) for inner in ast.walk(node)):
            found[ast.unparse(node)] += 1
    return found


def introduced_fallbacks(original: str, repaired: str, stderr: str) -> list[str]:
    """What the repair added that turns the missing value of the traceback into a default or into silence."""
    if 'KeyError' not in stderr and 'IndexError' not in stderr:
        return []
    before, after = _parse(original), _parse(repaired)
    if before is None or after is None:
        return []
    missing = set(re.findall(r"KeyError:\s*['\"]([^'\"]+)['\"]", stderr))
    found = []
    for (key, arguments, text), count in (_get_calls(after) - _get_calls(before)).items():
        if key in missing and (arguments >= 2 or not _checked_out_loud(after, text)):
            found += [text] * count
    for text, count in (_swallowing_handlers(after) - _swallowing_handlers(before)).items():
        found += [text.splitlines()[0].rstrip(':')] * count
    return list(dict.fromkeys(found))
