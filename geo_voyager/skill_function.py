"""A Skill as one named function, so that Skills can call each other (as in MineDojo/Voyager).

The code of a Skill is imports and exactly one top-level function with a docstring. The docstring is the Skill's
description; the function's name is how other code calls it. Nothing else runs at the top level, so loading a Skill
to make it callable has no effect of its own.
"""
import ast
import builtins
from dataclasses import dataclass

_BUILTINS = frozenset(dir(builtins))


@dataclass(frozen=True)
class SkillFunction:
    name: str
    parameters: tuple[str, ...]
    description: str
    code: str
    calls: tuple[str, ...]      # names the function calls that are neither builtins nor its own: Skills or primitives


def _own_names(function: ast.FunctionDef) -> set[str]:
    names = {arg.arg for arg in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}
    names |= {a.arg for a in (function.args.vararg, function.args.kwarg) if a is not None}
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not function:
            if not isinstance(node, ast.Lambda):
                names.add(node.name)
            names |= {arg.arg for arg in node.args.args}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def called_names(tree: ast.AST, own: set[str] = frozenset()) -> tuple[str, ...]:
    """The plain names called in the tree, in first-seen order, without builtins and the given names."""
    seen = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in _BUILTINS and name not in own and name not in seen:
                seen.append(name)
    return tuple(seen)


def parse_skill(code: str) -> SkillFunction:
    code = code.strip()
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        raise ValueError(f'A Skill must parse as Python: {error}') from None
    if any(isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef)) for node in tree.body):
        raise ValueError('A Skill must be exactly one function (a top-level def), not async and not a class')
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(functions) != 1:
        raise ValueError(f'A Skill must be exactly one function (a top-level def), not {len(functions)}')
    if any(not isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom)) for node in tree.body):
        raise ValueError('A Skill may have only imports besides its function: nothing may run when it is loaded')
    function = functions[0]
    if not function.name.isidentifier() or function.name.startswith('_'):
        raise ValueError(f'A Skill needs a public function name, not {function.name!r}')
    description = ast.get_docstring(function)
    if not description or not description.strip():
        raise ValueError('A Skill function needs a docstring that says what it does')
    arguments = function.args
    parameters = tuple(arg.arg for arg in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs))
    calls = called_names(function, _own_names(function) | {function.name})
    return SkillFunction(function.name, parameters, description.strip(), code, calls)
