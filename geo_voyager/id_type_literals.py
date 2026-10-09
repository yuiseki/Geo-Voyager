"""Code that compares the id_type of a target with a fixed string.

intent_target["id_type"] says what kind of id the target has ('relation_id', 'id', ...). The code is to use
intent_target["id_value"] as it is. A branch on id_type == 'relation' is a guess about the spelling: when the guess
is wrong the branch is never taken, the id is used unconverted, and a count over the wrong area is 0 without any error.
"""
import ast


def _reads_id_type(node: ast.AST, names: set[str]) -> bool:
    if isinstance(node, ast.Subscript):
        return isinstance(node.slice, ast.Constant) and node.slice.value == 'id_type'
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get':
        return bool(node.args) and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'id_type'
    return isinstance(node, ast.Name) and node.id in names


def _fixed_strings(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return bool(node.elts) and all(_fixed_strings(item) for item in node.elts)
    return False


def id_type_comparisons(code: str) -> list[str]:
    """The comparisons of an id_type with a fixed string, as written. Empty when the code does not parse."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _reads_id_type(node.value, set()):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
            sides = (node.left, node.comparators[0])
            if any(_reads_id_type(a, names) and _fixed_strings(b) for a, b in (sides, sides[::-1])):
                found.append(ast.unparse(node))
    return found
