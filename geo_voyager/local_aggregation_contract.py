"""Two mistakes the code of a local aggregation must not make, found without a model.

A local aggregation works only on the Observations of earlier steps. Two things have gone wrong in it:
- a measurement that is not there is turned into a value: o.get("count", 0). A lookup that found the wrong
  object then reads as a count of 0, and the comparison on top of it as a tie;
- an Observation is picked by its place in the list: decoded[2]. The order of the steps is not what the
  Observation means, and it changes when a step is repeated or the Planner plans another way.
The remedy is the same as for a target: find the object by its name and id, and let a missing field raise.
"""
import ast


def _mentions(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(item, ast.Name) and item.id in names for item in ast.walk(node))


def _filters(node: ast.AST) -> bool:
    """A comprehension with an if: its result is a selection by a condition, and its first item is not a place in the list."""
    return isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)) and any(g.ifs for g in node.generators)


def _is_position(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


def _is_false_default(node: ast.AST) -> bool:
    """A default that passes for a measurement: a number or None. An empty string (a label) or an empty list or dict is only 'nothing there'."""
    return isinstance(node, ast.Constant) and (node.value is None or
                                               (isinstance(node.value, (int, float)) and not isinstance(node.value, bool)))


def local_aggregation_violations(code: str, observation_count: int | None = None) -> list[str]:
    """The defaulted measurements and the positional picks of Observations, as written. Empty if the code does not parse.

    With exactly one earlier Observation there is nothing to choose between, and previous_observations[0] is simply
    that Observation (the Generator is shown it that way). Position is a mistake only when there are several.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    observations = {'previous_observations'}
    for _ in range(3):                         # decoded = [json.loads(t) for t in previous_observations], rows = list(decoded)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _mentions(node.value, observations) and not _filters(node.value):
                observations.update(target.id for target in node.targets if isinstance(target, ast.Name))
    found = []
    for node in ast.walk(tree):
        if observation_count != 1 and isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in observations and _is_position(node.slice):
            found.append(ast.unparse(node))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get' \
                and len(node.args) == 2 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) \
                and _is_false_default(node.args[1]):
            found.append(ast.unparse(node))
    return found
