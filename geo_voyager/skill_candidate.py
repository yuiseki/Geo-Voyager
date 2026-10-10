"""A candidate: the code the Generator (or a repair) wrote for one Intent, before it is known to work.

The code is a short program. It may call saved Skills by name (they are linked in front of it when it runs), and it
may define one new function: the new Skill, which is saved when the Critic accepts the run. The program's top-level
lines pass the runtime values (intent_target, previous_observations, dataset_id, intent_text) to the functions as
arguments; a function that reads them directly would only work for this one Intent.
"""
import ast
from dataclasses import dataclass
import re

from .skill_function import parse_skill

TRIPLE_QUOTE = '"' * 3
RUNTIME_NAMES = ('intent_target', 'previous_observations', 'dataset_id', 'intent_text')


@dataclass(frozen=True)
class SkillCandidate:
    code: str
    description: str


def _functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def new_skill_code(code: str, description: str = '') -> str | None:
    """The new Skill in a candidate: its imports and its one function. None when it defines no function.

    A local model often leaves out the docstring. The candidate's own description (its 説明) then becomes it.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    functions = _functions(tree)
    if len(functions) != 1:
        return None
    imports = [ast.get_source_segment(code, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    function = functions[0]
    source = ast.get_source_segment(code, function)
    if ast.get_docstring(function) is None and description.strip():
        lines = source.splitlines()
        header = function.body[0].lineno - function.lineno          # the lines of the signature
        indent = ' ' * function.body[0].col_offset
        text = ' '.join(description.split()).replace(TRIPLE_QUOTE, "'''")
        source = '\n'.join(lines[:header] + [indent + TRIPLE_QUOTE + text + TRIPLE_QUOTE] + lines[header:])
    return '\n'.join(imports) + ('\n\n\n' if imports else '') + source


def _returns_a_value(function: ast.FunctionDef) -> bool:
    """A return with a value in the function itself, not in a function nested in it."""
    stack = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return) and node.value is not None:
            return True
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return False


def skill_shape_problems(code: str, shown: tuple[str, ...] = ()) -> list[str]:
    """Why the candidate does not yield a reusable Skill: no function and no call to a shown Skill, more than one
    function, no docstring, no returned value, or a function that reads a runtime value instead of taking it as an
    argument. Empty when there is nothing wrong. Like Voyager, every run either reuses a Skill or writes one."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []           # the run reports it
    functions = _functions(tree)
    if len(functions) > 1:
        return [f'more than one function: {", ".join(f.name for f in functions)}']
    if not functions:
        called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        if called & set(shown):
            return []
        return ['関数が無い: 処理を名前と引数と docstring を持つ関数 1 つにまとめるか、見せた Skill を呼ぶ']
    try:
        parse_skill(new_skill_code(code, description='(the candidate description)') or '')
    except ValueError as error:
        return [str(error)]
    function = functions[0]
    if not _returns_a_value(function):
        return [f'the function {function.name} does not return its result; return it and print it where it is called']
    parameters = {a.arg for a in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}
    read = sorted({node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                   and node.id in RUNTIME_NAMES and node.id not in parameters})
    return [f'the function {function.name} reads {name} directly; take it as an argument' for name in read]


def _same_function(a: ast.FunctionDef, b: ast.FunctionDef) -> bool:
    """The same function apart from comments, blank lines and the docstring's layout."""
    def body(function):
        nodes = function.body[1:] if ast.get_docstring(function) is not None else function.body
        return [ast.dump(node) for node in nodes], ast.dump(function.args), (ast.get_docstring(function) or '').split()
    return a.name == b.name and body(a) == body(b)


def drop_copied_skills(code: str, library) -> str:
    """The code without the definitions it copied from saved Skills, so that the saved Skills are called instead.

    A local model shown a Skill often writes its definition out again instead of calling it. When the copy is the
    same function as the saved version, the definition is removed, and linking puts the saved one in front. A
    definition that differs is a new version of the Skill and is kept.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    saved = set(library.names())
    lines = code.splitlines(keepends=True)
    for function in reversed(_functions(tree)):
        if function.name not in saved or not isinstance(function, ast.FunctionDef):
            continue
        original = next(node for node in ast.parse(library.get(function.name).code).body if isinstance(node, ast.FunctionDef))
        if _same_function(function, original):
            start = (function.decorator_list[0].lineno if function.decorator_list else function.lineno) - 1
            del lines[start:function.end_lineno]
    result = ''.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip('\n') if result != code else code
