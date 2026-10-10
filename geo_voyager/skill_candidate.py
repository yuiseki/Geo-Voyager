"""A candidate: the code the Generator (or a repair) wrote for one Intent, before it is known to work.

The code is a short program. It may call saved Skills by name (they are linked in front of it when it runs), and it
may define one new function: the new Skill, which is saved when the Critic accepts the run. The program's top-level
lines pass the runtime values (intent_target, previous_observations, dataset_id, intent_text) to the functions as
arguments; a function that reads them directly would only work for this one Intent.
"""
import ast
from dataclasses import dataclass

from .skill_function import parse_skill

RUNTIME_NAMES = ('intent_target', 'previous_observations', 'dataset_id', 'intent_text')


@dataclass(frozen=True)
class SkillCandidate:
    code: str
    description: str


def _functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def new_skill_code(code: str) -> str | None:
    """The new Skill in a candidate: its imports and its one function. None when it defines no function."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    functions = _functions(tree)
    if len(functions) != 1:
        return None
    imports = [ast.get_source_segment(code, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    return '\n'.join(imports) + ('\n\n\n' if imports else '') + ast.get_source_segment(code, functions[0])


def skill_shape_problems(code: str) -> list[str]:
    """Why the candidate's new function can not become a Skill: more than one function, no docstring, or a
    function that reads a runtime value instead of taking it as an argument. Empty when there is nothing wrong."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []           # the run reports it
    functions = _functions(tree)
    if len(functions) > 1:
        return [f'more than one function: {", ".join(f.name for f in functions)}']
    if not functions:
        return []
    try:
        parse_skill(new_skill_code(code) or '')
    except ValueError as error:
        return [str(error)]
    function = functions[0]
    parameters = {a.arg for a in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}
    read = sorted({node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                   and node.id in RUNTIME_NAMES and node.id not in parameters})
    return [f'the function {function.name} reads {name} directly; take it as an argument' for name in read]
